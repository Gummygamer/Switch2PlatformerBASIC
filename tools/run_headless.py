"""Execute this game's BASIC subset through Python translation.

Not a SmileBASIC emulator or syntax/SDK compatibility test. Graphics commands
validate/evaluate arguments and record calls; input is scripted. Only trusted
local BASIC source should be used (expressions are evaluated as Python).
"""
import argparse
from collections import Counter, defaultdict
import math
from pathlib import Path
import re


def split(text, separator):
    return re.split(separator + r'(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)', text)


def expression(text):
    parts = re.split(r'("[^\"]*")', text)
    for i in range(0, len(parts), 2):
        s = parts[i]
        s = s.replace('#PI', repr(math.pi))
        s = re.sub(r'#(B_\w+)', r'"\1"', s)
        s = re.sub(r'\bAND\b', 'and', s)
        s = re.sub(r'\bOR\b', 'or', s)
        s = s.replace('^', '**')
        s = re.sub(r'(?<![<>=!])=(?!=)', '==', s)
        # BASIC scalars default to zero; arrays/functions are initialized below.
        s = re.sub(r'\b[A-Z][A-Z0-9_]*\b(?![\w]*(?:\s*\())',
                   lambda m: f'v[{m[0]!r}]' if not m[0].startswith('B_') else m[0], s)
        parts[i] = s
    return ''.join(parts)


class Runner:
    def __init__(self, path):
        self.v = defaultdict(float)
        self.frame = 0
        self.calls = Counter()
        self.lines = Counter()
        self.hud = []
        self.data = []
        self.read_index = 0
        self.stick = 0
        self.buttons = set()
        self.source = path.read_text().splitlines()
        for line in self.source:
            if line.startswith('DATA '):
                self.data.extend(map(float, line[5:].split(',')))
        self.env = dict(v=self.v, ABS=abs, MIN=min, MAX=max, SQR=math.sqrt,
                        FLOOR=math.floor, SIN=math.sin, COS=math.cos,
                        RGB=lambda r,g,b: (int(r)<<16)|(int(g)<<8)|int(b),
                        BUTTON=lambda port, button, *mode: int(button in self.buttons),
                        read=self.read, draw=self.draw, emit=self.hud.append,
                        hit=self.hit, stick=lambda: self.stick,
                        inclusive=lambda a,b: range(int(a),int(b)+1))
        generated = self.translate()
        self.generated = generated
        exec(compile(generated, str(path) + ' [translated]', 'exec'), self.env)
        self.env['init']()

    def read(self):
        value = self.data[self.read_index]
        self.read_index += 1
        return value

    def hit(self, line):
        self.lines[line] += 1
        self.current_line = line

    def draw(self, name, *args):
        assert all(math.isfinite(x) for x in args), (name, args)
        self.calls[name] += 1

    def translate(self):
        out = []
        indent = 0
        def add(s):
            out.append('    '*indent+s)
        add('def init():')
        indent = 1
        for number, raw in enumerate(self.source, 1):
            line = raw.strip()
            if not line or line.startswith("'") or line.startswith('DATA '):
                continue
            if line.startswith('@'):
                indent = 0
                add('def '+line[1:]+'():')
                indent = 1
                if line == '@WORLD':
                    add('pass')
                continue
            if line in ('NEXT', 'ENDIF', 'ELSE'):
                indent -= 1
                if line == 'ELSE':
                    add('else:')
                    indent += 1
                continue
            add(f'hit({number})')
            conditional = False
            if line.startswith('IF '):
                cond, line = line[3:].split(' THEN', 1)
                add('if '+expression(cond)+':')
                indent += 1
                line = line.strip()
                if not line:
                    continue
                conditional = True
            for stmt in split(line, ':'):
                stmt = stmt.strip()
                cmd, _, args = stmt.partition(' ')
                if cmd == 'FOR':
                    match = re.fullmatch(r'(\w+)=(.*?) TO (.*)', args)
                    name, start, end = match.groups()
                    add(f'for v[{name!r}] in inclusive({expression(start)}, {expression(end)}):')
                    indent += 1
                elif cmd == 'DIM':
                    for name, size in re.findall(r'(\w+)\[(\d+)\]', args):
                        add(f'v[{name!r}] = [0.0]*{size}')
                elif cmd == 'READ':
                    for target in args.split(','):
                        add(expression(target)+' = read()')
                elif cmd == 'RESTORE':
                    assert args == '@WORLD'
                elif cmd == 'GOSUB':
                    add(args[1:]+'()')
                elif cmd == 'GOTO':
                    assert args == '@MAIN'
                    add('return')
                elif cmd == 'RETURN':
                    add('return')
                elif cmd == 'STICK':
                    add("v['INPUTX'] = stick(); v['INPUTY'] = 0")
                elif cmd == 'PRINT':
                    add('emit("".join(map(str, ['+', '.join(expression(s) for s in split(args, ';'))+'])))')
                elif cmd in ('ACLS', 'XSCREEN', 'GCLS', 'GFILL', 'GLINE', 'GCIRCLE', 'GBOX', 'LOCATE', 'VSYNC'):
                    add(f'draw({cmd!r}'+(', '+expression(args) if args else '')+')')
                elif '=' in stmt:
                    target, value = stmt.split('=', 1)
                    add(expression(target)+' = '+expression(value))
                else:
                    raise ValueError(f'Unsupported statement at {number}: {stmt}')
            if conditional:
                indent -= 1
        return '\n'.join(out)+'\n'

    def run_frame(self, stick=0, buttons=()):
        self.stick, self.buttons = stick, set(buttons)
        self.hud.clear()
        try:
            self.env['MAIN']()
            for name in ('X', 'Y', 'VX', 'VY', 'OMEGA', 'ANGLE'):
                assert math.isfinite(self.v[name]), name
        except Exception as error:
            raise RuntimeError(f'BASIC line {self.current_line}: {self.source[self.current_line-1]}') from error
        self.frame += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=int, default=120)
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / 'GRAVITY.BAS'
    runner = Runner(path)
    for _ in range(args.frames):
        runner.run_frame()
    assert runner.v['GROUNDED'] == 1
    assert abs(runner.v['Y'] - 7.75) < .01
    print(f'PASS: {args.frames} idle frames; disk rests at ({runner.v["X"]:.3f}, {runner.v["Y"]:.3f})')
    for angle in (101, -101):
        runner.v['ANGLE'] = angle
        runner.run_frame()
        assert 0 <= runner.v['ANGLE'] < 2*math.pi
    print('PASS: positive and negative angle wrap at BASIC line 159')
    runner.run_frame(buttons=['B_RRIGHT'])
    assert runner.v['VY'] < -5
    print('PASS: jump from resting surface')
    for frame in range(args.frames):
        runner.run_frame(stick=1 if frame < args.frames//2 else -1,
                         buttons=['B_RDOWN'] if frame % 30 < 5 else [])
    for x, y in ((26,3.5), (34,5), (44,4), (52,3.5)):
        runner.v.update(X=x, Y=y, VX=2, VY=1)
        for _ in range(10):
            runner.run_frame()
        if x == 34:
            assert runner.v['EY'] == -5
        if x == 44:
            assert runner.v['BZ'] == 1.6
    assert runner.v['WON'] == 1
    assert any('FINISH!' in line for line in runner.hud)
    assert runner.v['HOME'] == 26
    runner.run_frame(buttons=['B_RLEFT'])
    assert runner.v['EM'] == 0
    runner.run_frame(buttons=['B_RLEFT'])
    assert runner.v['EM'] == 1
    runner.v['Y'] = 25
    runner.run_frame()
    assert runner.v['DEATHS'] >= 1 and runner.v['X'] == 26
    runner.run_frame(buttons=['B_RUP'])
    assert runner.v['X'] == 26
    for line in (242, 243, 244, 54, 55):
        assert runner.lines[line] > 0
    print('PASS: movement/brake, checkpoint, electric/magnetic regions, finish HUD, field toggle, fall/reset, respawn')
    print(f'PASS: {runner.frame} frames; {sum(runner.calls.values())} API calls recorded; end of DRAW and loop continuation executed')
    print('LIMIT: custom Python semantics; graphics/input are stubs; does not validate SmileBASIC syntax or API compatibility')


if __name__ == '__main__':
    main()

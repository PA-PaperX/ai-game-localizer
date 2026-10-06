"""Small, explicit Unreal text-format adapter; unknown nested syntax stays blocked."""
from collections import Counter
import re


def unreal_validate(source, target, basic_validate, error):
    if not isinstance(target, str):
        raise error('Target must be text')
    # Unreal input/image substitutions in backticks are opaque engine data.
    pattern = r'`[^`]*`'
    if Counter(re.findall(pattern, source)) != Counter(re.findall(pattern, target)):
        raise error('Unreal input/image token differs from source')
    clean_source, clean_target = [re.sub(pattern, '', t) for t in (source, target)]
    plural_pattern = r'\|plural\(([^()]*)\)'
    plurals = [list(re.finditer(plural_pattern, t)) for t in (clean_source, clean_target)]
    if len(plurals[0]) != len(plurals[1]):
        raise error('Unreal plural expression count changed')
    for left, right in zip(*plurals):
        def branches(expression):
            result = []
            for item in expression.group(1).split(','):
                label, separator, text = item.partition('=')
                if not separator or label.strip() not in ('zero','one','two','few','many','other'):
                    raise error('Unsupported Unreal plural branch')
                result.append((label.strip(), text))
            if len({label for label, _ in result}) != len(result):
                raise error('Duplicate Unreal plural branch')
            return result
        a, b = branches(left), branches(right)
        if [k for k, _ in a] != [k for k, _ in b]:
            raise error('Unreal plural branch labels/order changed')
        for (_, a_text), (_, b_text) in zip(a, b):
            basic_validate(a_text, b_text)
    clean_source, clean_target = [re.sub(plural_pattern, '', t) for t in (clean_source, clean_target)]
    # Bare Slate closing tags are engine syntax, too.
    if clean_source.count('</>') != clean_target.count('</>'):
        raise error('Slate closing tag count changed')
    basic_validate(clean_source, clean_target)

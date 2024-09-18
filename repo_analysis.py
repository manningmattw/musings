import os
import ast


def extract_definitions(node):
    definitions = None

    if isinstance(node, ast.ClassDef):
        definitions = dict()

        for subnode in node.body:
            if isinstance(subnode, ast.ClassDef):
                definitions[subnode.name] = extract_definitions(subnode)

            elif isinstance(subnode, ast.FunctionDef):
                definitions[subnode.name] = sum(1 for l in ast.unparse(subnode).splitlines() if l)

        return definitions

    if isinstance(node, ast.FunctionDef) and isinstance(node, ast.Module):
        definitions = sum(1 for l in ast.unparse(node).splitlines() if l)

    return definitions


def has_actual_code(tree, include_imports=True):
    count = 0

    for node in tree.body:
        if not include_imports and isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            continue

        count += 1

    return bool(count)


def extract_module(python_file):
    with open(python_file, 'r', encoding='utf-8') as file:
        file_content = file.read()

    lines_of_code = sum(1 for l in file_content.splitlines() if l)

    try:
        root_node = ast.parse(file_content, filename=python_file)

        if not has_actual_code(root_node, include_imports=False):
            return None

        definitions = dict()

        for node in ast.walk(root_node):
            node_definitions = extract_definitions(node)

            if node_definitions:
                definitions[node.name] = node_definitions


        if not definitions:
            return None

        return {
            'lines_of_code': lines_of_code,
            'definitions': definitions,
            'error': None}

    except Exception as e:
        return {
            'lines_of_code': lines_of_code,
            'definitions': dict(),
            'error': e}


def analyze_repo(repo_path):
    repo_outline = {'root': dict()}

    # Walk through the directory tree of the repo
    for dirpath, _, filenames in os.walk(repo_path):
        python_files = [f for f in filenames if f.endswith('.py')]

        for python_file in python_files:
            file_path = os.path.join(dirpath, python_file)

            module = extract_module(file_path)

            relative_path = os.path.relpath(file_path, repo_path)
            relative_dir = os.path.dirname(relative_path)

            if relative_dir:
                if relative_dir not in repo_outline:
                    repo_outline[relative_dir] = dict()

                repo_outline[relative_dir][python_file] = module

            else:
                repo_outline['root'][python_file] = module

    return repo_outline


def print_definitions(definition_name, definition, indent):
    lines = ""

    if isinstance(definition, dict):
        lines += f"{'    ' * indent}{definition_name} (class)\n"

        for class_name, class_definitions in definition.items():
            lines += print_definitions(class_name, class_definitions, indent + 1)

    if isinstance(definition, int):
        lines += f"{'    ' * indent}{definition_name} (function): {definition} objects\n"

    return lines


def print_repo_outline(repo_outline):
    lines = ""

    dir_names = sorted([(d.split('/'), f) for d, f in repo_outline.items() if d != 'root'], key=lambda k: k[0])
    file_names = sorted(list(repo_outline['root'].items()), key=lambda k: k[0])

    printed_dirs = set()

    for dir_name_list, python_files in dir_names:
        dir_lines = ""
        add_dir_lines = False

        for indent, dir_name in enumerate(dir_name_list, start=1):
            dir_path = '/'.join(dir_name_list[:indent])

            if dir_path not in printed_dirs:
                dir_lines += f"{'    ' * (indent - 1)}{dir_name}/\n"
                printed_dirs.add(dir_path)

        for file_name, module in python_files.items():
            definitions = (module or dict()).get('definitions', dict())
            error = (module or dict()).get('error', None)

            if not definitions and not error:
                continue

            add_dir_lines = True

            dir_lines += f"{'    ' * indent}{file_name} (module)\n"

            for definition_name, definition in definitions.items():
                dir_lines += print_definitions(definition_name, definition, indent + 1)

        if add_dir_lines:
            lines += dir_lines

    for file_name, module in file_names:
        if file_name == 'repo_analysis.py':
            continue

        definitions = (module or dict()).get('definitions', dict())
        error = (module or dict()).get('error', None)

        if not definitions and not error:
            continue

        lines += f"{file_name} (module)\n"

        for definition_name, definition in definitions.items():
            lines += print_definitions(definition_name, definition, 1)

    with open('repo_analysis.txt', 'w') as f:
        f.writelines(lines)


if __name__ == '__main__':
    repo_outline = analyze_repo(os.getcwd())

    print_repo_outline(repo_outline)

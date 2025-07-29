#!/usr/bin/env python3
"""
Скрипт для генерации TreeView.md - документа со структурой проекта.
Включает информацию о файлах, классах, функциях и методах.
Версия: v002
"""

import os
import ast
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import subprocess
import json
import inspect

class TreeViewGenerator:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.tree_data = []
        # Расширенный список игнорируемых директорий
        self.ignored_dirs = {
            '.git', '__pycache__', '.venv', 'venv', '.idea', 
            'node_modules', '.pytest_cache', '.coverage', 
            'htmlcov', 'dist', 'build', '*.egg-info',
            'ffmpeg', 'voice_messages', 'google_credentials',
            '.mypy_cache', '.tox', '.nox', '.hypothesis',
            '.ruff_cache', 'site-packages', 'lib64', 'share',
            'bin', 'include', 'migrations', '__pypackages__'
        }
        # Расширенный список игнорируемых файлов и расширений
        self.ignored_files = {
            '.DS_Store', '*.pyc', '*.pyo', '*.pyd', 
            '.Python', '*.so', '*.dylib', '*.log',
            '*.lock', '.env', '.env.*', '*.tmp',
            '*.temp', '*.cache', '*.bak', '*.swp',
            '*.swo', '*~', '.coverage', '*.pid',
            'Thumbs.db', 'desktop.ini', '*.orig'
        }
        # Поддерживаемые языки программирования
        self.supported_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', 
            '.cpp', '.c', '.h', '.hpp', '.cs', '.go', 
            '.rs', '.php', '.rb', '.swift', '.kt', '.scala',
            '.r', '.m', '.mm', '.f90', '.jl', '.lua'
        }
        
    def should_ignore(self, path: Path) -> bool:
        """Проверка, нужно ли игнорировать файл или директорию."""
        name = path.name
        
        # Проверка директорий
        if path.is_dir():
            if name in self.ignored_dirs:
                return True
            if name.startswith('.') and name not in ['.github', '.gitlab']:
                return True
                
        # Проверка файлов
        if path.is_file():
            # Прямое совпадение
            if name in self.ignored_files:
                return True
            # Проверка по паттернам
            for pattern in self.ignored_files:
                if '*' in pattern:
                    if pattern.startswith('*'):
                        ext = pattern.replace('*', '')
                        if name.endswith(ext):
                            return True
                    elif pattern.endswith('*'):
                        prefix = pattern.replace('*', '')
                        if name.startswith(prefix):
                            return True
                            
        return False
        
    def get_function_signature(self, node: ast.FunctionDef) -> str:
        """Извлечение сигнатуры функции с параметрами."""
        args = []
        
        # Обычные аргументы
        for i, arg in enumerate(node.args.args):
            arg_str = arg.arg
            # Добавляем значения по умолчанию если есть
            defaults_offset = len(node.args.args) - len(node.args.defaults)
            if i >= defaults_offset:
                default_index = i - defaults_offset
                if default_index < len(node.args.defaults):
                    default = node.args.defaults[default_index]
                    if isinstance(default, ast.Constant):
                        arg_str += f"={repr(default.value)}"
                    else:
                        arg_str += "=..."
            args.append(arg_str)
            
        # *args
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
            
        # keyword-only аргументы
        for i, arg in enumerate(node.args.kwonlyargs):
            arg_str = arg.arg
            if i < len(node.args.kw_defaults) and node.args.kw_defaults[i]:
                default = node.args.kw_defaults[i]
                if isinstance(default, ast.Constant):
                    arg_str += f"={repr(default.value)}"
                else:
                    arg_str += "=..."
            args.append(arg_str)
            
        # **kwargs
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
            
        return f"{node.name}({', '.join(args)})"
        
    def extract_python_structure(self, file_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Извлечение структуры Python файла (классы, функции, методы)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            structure = {
                'classes': [],
                'functions': [],
                'imports': []
            }
            
            # Извлекаем импорты для контекста
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        structure['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        structure['imports'].append(f"{module}.{alias.name}")
            
            # Обрабатываем классы
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'line': node.lineno,
                        'methods': [],
                        'docstring': ast.get_docstring(node),
                        'bases': [self._get_node_name(base) for base in node.bases]
                    }
                    
                    # Извлекаем методы класса
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Не включаем вложенные функции внутри методов
                            method_info = {
                                'name': item.name,
                                'line': item.lineno,
                                'signature': self.get_function_signature(item),
                                'docstring': ast.get_docstring(item),
                                'is_static': any(isinstance(d, ast.Name) and d.id == 'staticmethod' 
                                               for d in item.decorator_list),
                                'is_class': any(isinstance(d, ast.Name) and d.id == 'classmethod' 
                                              for d in item.decorator_list),
                                'is_property': any(isinstance(d, ast.Name) and d.id == 'property' 
                                                 for d in item.decorator_list)
                            }
                            class_info['methods'].append(method_info)
                            
                    structure['classes'].append(class_info)
                    
                # Обрабатываем функции верхнего уровня (не вложенные)
                elif isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'line': node.lineno,
                        'signature': self.get_function_signature(node),
                        'docstring': ast.get_docstring(node),
                        'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    }
                    structure['functions'].append(func_info)
                    
            return structure
            
        except Exception as e:
            print(f"Ошибка при парсинге {file_path}: {e}")
            return {'classes': [], 'functions': [], 'imports': []}
            
    def _get_node_name(self, node) -> str:
        """Получение имени узла AST."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_node_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        else:
            return str(type(node).__name__)
            
    def _get_decorator_name(self, decorator) -> str:
        """Получение имени декоратора."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            return self._get_node_name(decorator.func)
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_node_name(decorator.value)}.{decorator.attr}"
        else:
            return str(type(decorator).__name__)
            
    def build_tree(self, directory: Path, prefix: str = "", is_last: bool = True) -> str:
        """Построение дерева директорий с информацией о структуре кода."""
        if self.should_ignore(directory):
            return ""
            
        output = []
        relative_path = directory.relative_to(self.project_root)
        
        # Добавляем текущую директорию
        if directory != self.project_root:
            tree_symbol = "└── " if is_last else "├── "
            output.append(f"{prefix}{tree_symbol}📁 **{directory.name}/** `{directory}`")
            
        # Получаем содержимое директории
        try:
            items = sorted(list(directory.iterdir()))
            dirs = [item for item in items if item.is_dir() and not self.should_ignore(item)]
            files = [item for item in items if item.is_file() and not self.should_ignore(item)]
            
            # Сначала обрабатываем файлы
            for i, file in enumerate(files):
                is_last_file = (i == len(files) - 1) and len(dirs) == 0
                file_prefix = prefix + ("    " if is_last else "│   ")
                file_symbol = "└── " if is_last_file else "├── "
                
                # Полный путь к файлу
                file_line = f"{file_prefix}{file_symbol}📄 `{file.name}`"
                
                # Для Python файлов добавляем структуру
                if file.suffix == '.py':
                    structure = self.extract_python_structure(file)
                    
                    if structure['classes'] or structure['functions']:
                        file_line += " - "
                        items_list = []
                        
                        if structure['classes']:
                            items_list.append(f"{len(structure['classes'])} класс(ов)")
                        if structure['functions']:
                            items_list.append(f"{len(structure['functions'])} функций")
                            
                        file_line += ", ".join(items_list)
                        
                    # Добавляем путь
                    file_line += f"\n{file_prefix}{'    ' if is_last_file else '│   '}  📍 Путь: `{file.relative_to(self.project_root)}`"
                        
                output.append(file_line)
                
                # Добавляем детали для Python файлов
                if file.suffix == '.py':
                    structure = self.extract_python_structure(file)
                    detail_prefix = file_prefix + ("    " if is_last_file else "│   ")
                    
                    # Функции
                    for func in structure['functions']:
                        func_line = f"{detail_prefix}  ⚡ `{func['signature']}` (строка {func['line']})"
                        if func['is_async']:
                            func_line += " [async]"
                        if func['decorators']:
                            func_line += f" [{', '.join(func['decorators'])}]"
                        output.append(func_line)
                        
                        # Добавляем описание функции если есть
                        if func['docstring']:
                            doc_lines = func['docstring'].split('\n')
                            first_line = doc_lines[0].strip()
                            if len(first_line) > 80:
                                first_line = first_line[:77] + "..."
                            output.append(f"{detail_prefix}    📝 {first_line}")
                        
                    # Классы
                    for cls in structure['classes']:
                        cls_line = f"{detail_prefix}  🏛️ `{cls['name']}`"
                        if cls['bases']:
                            cls_line += f"({', '.join(cls['bases'])})"
                        cls_line += f" (строка {cls['line']})"
                        output.append(cls_line)
                        
                        # Добавляем описание класса если есть
                        if cls['docstring']:
                            doc_lines = cls['docstring'].split('\n')
                            first_line = doc_lines[0].strip()
                            if len(first_line) > 80:
                                first_line = first_line[:77] + "..."
                            output.append(f"{detail_prefix}    📝 {first_line}")
                        
                        # Методы класса
                        for method in cls['methods']:
                            method_symbol = "└─"
                            method_line = f"{detail_prefix}    {method_symbol} `{method['signature']}` (строка {method['line']})"
                            
                            # Добавляем теги для специальных методов
                            tags = []
                            if method['is_static']:
                                tags.append('@staticmethod')
                            if method['is_class']:
                                tags.append('@classmethod')
                            if method['is_property']:
                                tags.append('@property')
                            if method['name'].startswith('__') and method['name'].endswith('__'):
                                tags.append('magic')
                                
                            if tags:
                                method_line += f" [{', '.join(tags)}]"
                                
                            output.append(method_line)
                            
            # Затем обрабатываем поддиректории
            for i, subdir in enumerate(dirs):
                is_last_dir = (i == len(dirs) - 1)
                subdir_prefix = prefix + ("    " if is_last else "│   ")
                output.append(self.build_tree(subdir, subdir_prefix, is_last_dir))
                
        except PermissionError:
            pass
            
        return "\n".join(filter(None, output))        
    def generate_markdown(self) -> str:
        """Генерация полного Markdown документа."""
        output = [
            "# TreeView - Структура проекта FamilyFinanceProject",
            "",
            "Этот документ содержит полную структуру проекта с информацией о файлах, классах и функциях.",
            "Обновляется автоматически после внесения изменений в проект.",
            "",
            f"**Последнее обновление:** {self._get_timestamp()}",
            f"**Версия скрипта:** v002",
            "",
            "## Структура проекта",
            "",
            "```",
            f"📁 {self.project_root.name}/",
            self.build_tree(self.project_root, "", True),
            "```",
            "",
            "## Легенда",
            "",
            "- 📁 - Директория",
            "- 📄 - Файл",
            "- 📍 - Путь к файлу",
            "- ⚡ - Функция",
            "- 🏛️ - Класс", 
            "- └─ - Метод класса",
            "- 📝 - Описание (docstring)",
            "- [async] - Асинхронная функция",
            "- [@decorator] - Декоратор",
            "- [magic] - Магический метод",
            "",
            "## Статистика проекта",
            "",
            self._generate_statistics(),
            "",
            "## Поддерживаемые языки",
            "",
            "Скрипт анализирует файлы следующих языков программирования:",
            "Python, JavaScript, TypeScript, Java, C/C++, C#, Go, Rust, PHP, Ruby, Swift, Kotlin, Scala, R, Objective-C, Fortran, Julia, Lua",
            "",
            "## Игнорируемые файлы и директории",
            "",
            "Автоматически исключаются:",
            "- Системные и временные файлы",
            "- Директории виртуальных окружений",
            "- Кэш и артефакты сборки", 
            "- Файлы конфигурации IDE",
            ""
        ]
        
        return "\n".join(output)        
    def _get_timestamp(self) -> str:
        """Получение текущей временной метки."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def _generate_statistics(self) -> str:
        """Генерация статистики по проекту."""
        stats = {
            'total_files': 0,
            'python_files': 0,
            'total_lines': 0,
            'total_classes': 0,
            'total_functions': 0,
            'total_methods': 0,
            'files_by_extension': {}
        }
        
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            
            # Пропускаем игнорируемые директории
            dirs[:] = [d for d in dirs if not self.should_ignore(root_path / d)]
            
            for file in files:
                file_path = root_path / file
                if self.should_ignore(file_path):
                    continue
                    
                stats['total_files'] += 1
                
                # Подсчёт по расширениям
                ext = file_path.suffix.lower()
                if ext:
                    stats['files_by_extension'][ext] = stats['files_by_extension'].get(ext, 0) + 1
                
                # Подсчёт строк кода
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        stats['total_lines'] += len(lines)
                except Exception:
                    pass
                
                # Детальная статистика для Python файлов
                if file.endswith('.py'):
                    stats['python_files'] += 1
                    
                    try:
                        structure = self.extract_python_structure(file_path)
                        stats['total_classes'] += len(structure['classes'])
                        stats['total_functions'] += len(structure['functions'])
                        
                        # Подсчёт методов
                        for cls in structure['classes']:
                            stats['total_methods'] += len(cls['methods'])
                            
                    except Exception:
                        pass
                        
        # Форматирование статистики
        result = f"""- **Всего файлов:** {stats['total_files']}
- **Python файлов:** {stats['python_files']}
- **Строк кода:** {stats['total_lines']:,}
- **Классов:** {stats['total_classes']}
- **Функций:** {stats['total_functions']}
- **Методов:** {stats['total_methods']}

### Распределение файлов по типам:"""

        # Сортируем расширения по количеству файлов
        sorted_extensions = sorted(stats['files_by_extension'].items(), 
                                 key=lambda x: x[1], reverse=True)
        
        for ext, count in sorted_extensions[:10]:  # Топ-10 расширений
            result += f"\n- `{ext}`: {count} файлов"
            
        if len(sorted_extensions) > 10:
            others_count = sum(count for ext, count in sorted_extensions[10:])
            result += f"\n- Другие: {others_count} файлов"
            
        return result
    def generate(self, output_path: str):
        """Генерация и сохранение TreeView.md."""
        content = self.generate_markdown()
        
        # Создаём директорию если её нет
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ TreeView.md успешно создан: {output_path}")
        print(f"📊 Обработано {self._count_files()} файлов")
        
    def _count_files(self) -> int:
        """Подсчёт количества обработанных файлов."""
        count = 0
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            dirs[:] = [d for d in dirs if not self.should_ignore(root_path / d)]
            for file in files:
                if not self.should_ignore(root_path / file):
                    count += 1
        return count
        

def main():
    """Главная функция."""
    project_root = Path(__file__).parent.parent
    docs_path = project_root / "aidocs"
    
    # Создаем директорию aidocs, если её нет
    docs_path.mkdir(exist_ok=True)
    
    # Генерируем TreeView.md
    generator = TreeViewGenerator(str(project_root))
    generator.generate(str(docs_path / "treeview.md"))
    
    print("\n📌 Для автоматического обновления TreeView.md после изменений,")
    print("   запускайте: poetry run python generate_treeview.py")
    

if __name__ == "__main__":
    main()

import os
import re

def camel_to_snake(s):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()

def snake_to_pascal(s: str) -> str:
    return ''.join(word.title() for word in s.split('_'))

def main():
    # 获取用户输入
    base_name = input("Enter the class name (e.g., Product): ").strip()

    # 生成类名和文件名
    class_name = snake_to_pascal(base_name)
    file_base = camel_to_snake(class_name)
    lower_class = class_name[0].lower() + class_name[1:]

    # 默认输出目录为当前目录，可以手动修改
    output_dir = input("Enter output directory (leave empty for current directory): ").strip() or os.getcwd()

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 生成 Notifier 文件内容
    notifier_content = f"""import 'package:ap_ui/ap_ui.dart';

import '{file_base}_state.c.dart';

final {lower_class}Provider = StateNotifierProvider.autoDispose<{class_name}Notifier,
    {class_name}State>(
  (ref) => {class_name}NotifierImpl(),
);

abstract class {class_name}Notifier extends ApStateNotifier<{class_name}State> {{
  {class_name}Notifier(super.state);
}}

class {class_name}NotifierImpl extends {class_name}Notifier {{
  {class_name}NotifierImpl() : super({class_name}State.empty());
}}
"""

    # 生成 State 文件内容
    state_content = f"""import 'package:copy_with_extension/copy_with_extension.dart';

part '{file_base}_state.c.g.dart';

@CopyWith()
class {class_name}State {{
  const {class_name}State({{
    this.isLoading = false,
  }});

  factory {class_name}State.empty() {{
    return const {class_name}State();
  }}

  final bool isLoading;
}}
"""

    # 构建完整文件路径
    notifier_path = os.path.join(output_dir, f"{file_base}_notifier.dart")
    state_path = os.path.join(output_dir, f"{file_base}_state.c.dart")

    # 写入文件
    for path, content in [(notifier_path, notifier_content),
                          (state_path, state_content)]:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"Generated files at:\n{notifier_path}\n{state_path}")

if __name__ == "__main__":
    main()

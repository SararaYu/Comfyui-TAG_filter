import os
import re
from collections import OrderedDict

# 复用与单输出节点完全一致的加载/匹配逻辑风格 —— 但此文件是独立模块
class AdvancedDynamicTextFilterNode:
    BASE_PATH = os.path.dirname(os.path.realpath(__file__))
    DEFAULT_CONFIG = os.path.join(BASE_PATH, "config/filters.yml")
    FILE_PATHS = {
        "character": os.path.join(BASE_PATH, "config/character.txt"),
        "clothing": os.path.join(BASE_PATH, "config/clothing.txt"),
        "expression": os.path.join(BASE_PATH, "config/expression.txt"),
        "custom1": os.path.join(BASE_PATH, "config/custom1.txt"),
        "custom2": os.path.join(BASE_PATH, "config/custom2.txt"),
        "exclude": os.path.join(BASE_PATH, "config/exclude.txt")
    }

    def __init__(self):
        self.config_cache = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": OrderedDict([
                ("text_input", ("STRING", {"placeholder": "输入需要过滤的文本，用逗号或中文逗号分隔", "multiline": True})),

                ("character_toggle", ("BOOLEAN", {"default": True, "label": "角色过滤"})),
                ("clothing_toggle", ("BOOLEAN", {"default": True, "label": "服装过滤"})),
                ("expression_toggle", ("BOOLEAN", {"default": True, "label": "表情过滤"})),
                ("custom1_toggle", ("BOOLEAN", {"default": True, "label": "自定义1"})),
                ("custom2_toggle", ("BOOLEAN", {"default": True, "label": "自定义2"})),
                ("exclude_toggle", ("BOOLEAN", {"default": True, "label": "排除过滤"})),

                ("other_toggle", ("BOOLEAN", {"default": True, "label": "输出未分类标签（other）"})),

                ("debug_mode", ("BOOLEAN", {"default": False, "label": "调试模式"})),
            ])
        }

    # 输出：all, character, clothing, expression, custom1, custom2, other
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "all输出",
        "角色输出",
        "服装输出",
        "表情输出",
        "自定义1输出",
        "自定义2输出",
        "other输出",
    )
    FUNCTION = "apply_multi_output"
    CATEGORY = "Text/Filter"

    def load_features(self, path):
        try:
            if not os.path.exists(path):
                return set()

            mtime = os.path.getmtime(path)
            cached = self.config_cache.get(path, {})

            if cached.get('mtime', 0) < mtime:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()

                phrases = set()
                for line in re.split(r'[,\n]+', content):
                    phrase = line.strip()
                    if phrase:
                        phrases.add(phrase)
                self.config_cache[path] = {'mtime': mtime, 'data': phrases}
                print(f"[INFO] 从 {path} 加载了 {len(phrases)} 个过滤词")

            return self.config_cache[path]['data']

        except Exception as e:
            print(f"[WARN] 配置文件加载失败 ({path}): {str(e)}")
            return set()

    def get_category_features(self, category):
        global_data = self.load_features(self.DEFAULT_CONFIG)
        file_features = self.load_features(self.FILE_PATHS[category])
        return global_data.union(file_features)

    def apply_multi_output(self, **kwargs):
        debug_mode = kwargs.get("debug_mode", False)
        if debug_mode:
            print("\n=== 多输出过滤开始 ===")

        active_categories = {
            "character": kwargs["character_toggle"],
            "clothing": kwargs["clothing_toggle"],
            "expression": kwargs["expression_toggle"],
            "custom1": kwargs["custom1_toggle"],
            "custom2": kwargs["custom2_toggle"]
        }
        other_toggle = kwargs["other_toggle"]

        if debug_mode:
            print(f"开关状态: {active_categories}, other_toggle={other_toggle}")

        all_features = {cat: self.get_category_features(cat) for cat in active_categories.keys()}
        exclude_words = self.load_features(self.FILE_PATHS["exclude"]) if kwargs["exclude_toggle"] else set()

        raw_tags = [t.strip() for t in re.split(r'[，,]+', kwargs["text_input"]) if t.strip()]
        unique_tags = list(OrderedDict.fromkeys(raw_tags))

        if debug_mode:
            print(f"原始标签: {', '.join(unique_tags)}")

        # 为每个分类收集输出（顺序去重）
        category_outputs = {cat: [] for cat in active_categories.keys()}
        other_output = []

        for tag in unique_tags:
            tag_lower = tag.lower()
            # 排除检查
            if any(re.search(r'\b' + re.escape(phrase) + r'\b', tag_lower) for phrase in exclude_words):
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 被排除（排除词匹配）")
                continue

            exact_matches = set()
            substring_matches = set()
            for cat in active_categories.keys():
                for phrase in all_features[cat]:
                    pattern = r'\b' + re.escape(phrase) + r'\b'
                    if re.fullmatch(pattern, tag_lower):
                        exact_matches.add(cat)
                        break
                    elif re.search(pattern, tag_lower):
                        substring_matches.add(cat)
                        break

            matched_cats = exact_matches.union(substring_matches)

            if matched_cats:
                # 如果匹配到任意已关闭分类 -> 整条过滤（与原逻辑一致）
                inactive_matched = [c for c in matched_cats if not active_categories.get(c, False)]
                if inactive_matched:
                    if debug_mode:
                        print(f"[DEBUG] 标签 '{tag}' 匹配到已关闭分类 ({', '.join(inactive_matched)})，已过滤")
                    continue

                # 否则把标签加入到匹配到的每个（**开启的**）分类输出中
                for c in matched_cats:
                    if active_categories.get(c, False):
                        category_outputs[c].append(tag)
            else:
                # 未匹配任何分类：仅在 other_toggle 为 True 时保留
                if other_toggle:
                    other_output.append(tag)
                else:
                    if debug_mode:
                        print(f"[DEBUG] 标签 '{tag}' 未匹配任何分类，other 关闭，已过滤")

        # 顺序去重并拼接字符串输出
        for cat in category_outputs:
            category_outputs[cat] = ", ".join(OrderedDict.fromkeys(category_outputs[cat]))
        other_output = ", ".join(OrderedDict.fromkeys(other_output))

        # all 输出：合并所有开启分类的输出 + other（如果 other 开启）
        all_parts = []
        for cat, enabled in active_categories.items():
            if enabled and category_outputs.get(cat):
                all_parts.extend([p for p in category_outputs[cat].split(", ") if p])
        if other_toggle and other_output:
            all_parts.extend([p for p in other_output.split(", ") if p])

        all_output = ", ".join(OrderedDict.fromkeys([t for t in all_parts if t]))

        if debug_mode:
            print("=== 多输出过滤完成 ===")
            for k, v in category_outputs.items():
                print(f"  {k}: {v}")
            print(f"  other: {other_output}")
            print(f"  all: {all_output}")

        return (
            all_output,
            category_outputs["character"],
            category_outputs["clothing"],
            category_outputs["expression"],
            category_outputs["custom1"],
            category_outputs["custom2"],
            other_output,
        )

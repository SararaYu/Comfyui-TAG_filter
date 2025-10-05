import os
import re
from collections import OrderedDict

class DynamicTextFilterNode:
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

                # 开关均使用 BOOLEAN
                ("character_toggle", ("BOOLEAN", {"default": True, "label": "角色过滤"})),
                ("clothing_toggle", ("BOOLEAN", {"default": True, "label": "服装过滤"})),
                ("expression_toggle", ("BOOLEAN", {"default": True, "label": "表情过滤"})),
                ("custom1_toggle", ("BOOLEAN", {"default": True, "label": "自定义1"})),
                ("custom2_toggle", ("BOOLEAN", {"default": True, "label": "自定义2"})),
                ("exclude_toggle", ("BOOLEAN", {"default": True, "label": "排除过滤"})),

                # 新增 other 开关
                ("other_toggle", ("BOOLEAN", {"default": True, "label": "输出未分类标签（other）"})),

                ("debug_mode", ("BOOLEAN", {"default": False, "label": "调试模式"})),
            ])
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("总输出",)
    FUNCTION = "apply_filter"
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

    def apply_filter(self, **kwargs):
        debug_mode = kwargs.get("debug_mode", False)
        if debug_mode:
            print("\n=== 开始过滤处理 ===")

        # 初始化开关状态（布尔）
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

        # 加载所有分类特征（不依赖开关）
        all_features = {
            cat: self.get_category_features(cat)
            for cat in active_categories.keys()
        }

        # 排除词（若关闭 exclude 则为空集合）
        exclude_words = self.load_features(self.FILE_PATHS["exclude"]) if kwargs["exclude_toggle"] else set()

        # 解析输入标签（保持顺序并去重）
        raw_tags = [t.strip() for t in re.split(r'[，,]+', kwargs["text_input"]) if t.strip()]
        unique_tags = list(OrderedDict.fromkeys(raw_tags))

        if debug_mode:
            print(f"原始标签: {', '.join(unique_tags)}")

        # 标注每个标签的匹配情况
        tag_status = {}
        for tag in unique_tags:
            tag_lower = tag.lower()
            is_excluded = False

            # 排除检查（完整词边界）
            for phrase in exclude_words:
                if re.search(r'\b' + re.escape(phrase) + r'\b', tag_lower):
                    is_excluded = True
                    if debug_mode:
                        print(f"[DEBUG] 标签 '{tag}' 被排除词 '{phrase}' 匹配")
                    break

            if is_excluded:
                tag_status[tag] = {'exact': set(), 'substring': set(), 'excluded': True}
                continue

            exact_matches = set()
            substring_matches = set()

            # 遍历所有分类进行匹配（精确或子串）
            for cat in active_categories.keys():
                for phrase in all_features[cat]:
                    exact_pattern = r'\b' + re.escape(phrase) + r'\b'
                    if re.fullmatch(exact_pattern, tag_lower):
                        exact_matches.add(cat)
                        if debug_mode:
                            print(f"[DEBUG] 标签 '{tag}' 精确匹配分类 '{cat}' 的过滤词 '{phrase}'")
                    elif re.search(exact_pattern, tag_lower):
                        substring_matches.add(cat)
                        if debug_mode:
                            print(f"[DEBUG] 标签 '{tag}' 子串匹配分类 '{cat}' 的过滤词 '{phrase}'")

            tag_status[tag] = {
                'exact': exact_matches,
                'substring': substring_matches,
                'excluded': False
            }

        # 生成最终输出（严格遵循原有规则：匹配到任何关闭分类 -> 过滤）
        final_output = []
        for tag in unique_tags:
            status = tag_status[tag]

            if status['excluded']:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 被排除")
                continue

            # 是否匹配到任意分类（精确或子串）
            matched_cats = status['exact'].union(status['substring'])

            # 如果匹配到关闭的分类 -> 过滤（和最初实现一致）
            inactive_matched = [c for c in matched_cats if not active_categories.get(c, False)]
            if inactive_matched:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 匹配到已关闭分类 ({', '.join(inactive_matched)})，已过滤")
                continue

            # 如果匹配到至少一个开启的精确或子串匹配 -> 保留
            active_exact = [c for c in status['exact'] if active_categories.get(c, False)]
            if active_exact:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 被保留（精确匹配到开启分类: {', '.join(active_exact)})")
                final_output.append(tag)
                continue

            active_sub = [c for c in status['substring'] if active_categories.get(c, False)]
            if active_sub:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 被保留（子串匹配到开启分类: {', '.join(active_sub)})")
                final_output.append(tag)
                continue

            # 未匹配任何分类 —— 仅在 other_toggle=True 时保留
            if other_toggle:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 未匹配任何分类，other 开启，保留")
                final_output.append(tag)
            else:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 未匹配任何分类，other 关闭，已过滤")

        if debug_mode:
            print(f"过滤后标签: {', '.join(final_output)}")
            print("=== 过滤处理完成 ===\n")

        return (", ".join(final_output), )

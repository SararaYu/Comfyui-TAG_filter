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
                ("text_input", ("STRING", {"placeholder": "输入需要过滤的文本", "multiline": True})),
                ("character_toggle", ("INT", {"default": 1, "min": 0, "max": 1, "label": "角色过滤"})),
                ("clothing_toggle", ("INT", {"default": 1, "min": 0, "max": 1, "label": "服装过滤"})),
                ("expression_toggle", ("INT", {"default": 1, "min": 0, "max": 1, "label": "表情过滤"})),
                ("custom1_toggle", ("INT", {"default": 1, "min": 0, "max": 1, "label": "自定义1"})),
                ("custom2_toggle", ("INT", {"default": 1, "min": 0, "max": 1, "label": "自定义2"})),
                ("exclude_toggle", ("INT", {"default": 1, "min": 0, "max": 1, "label": "排除过滤"})),
                ("debug_mode", ("INT", {"default": 0, "min": 0, "max": 1, "label": "调试模式"}))
            ])
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("总输出",)
    FUNCTION = "apply_filter"

    def load_features(self, path):
        try:
            if not os.path.exists(path):
                return set()

            mtime = os.path.getmtime(path)
            cached = self.config_cache.get(path, {})

            if cached.get('mtime', 0) < mtime:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()

                # 处理为短语集合
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
        """获取指定分类的特征短语集合"""
        global_data = self.load_features(self.DEFAULT_CONFIG)
        file_features = self.load_features(self.FILE_PATHS[category])
        return global_data.union(file_features)

    def apply_filter(self, **kwargs):
        debug_mode = kwargs.get("debug_mode", 0)
        if debug_mode:
            print("\n=== 开始过滤处理 ===")

        # 初始化开关状态
        active_categories = {
            "character": kwargs["character_toggle"],
            "clothing": kwargs["clothing_toggle"],
            "expression": kwargs["expression_toggle"],
            "custom1": kwargs["custom1_toggle"],
            "custom2": kwargs["custom2_toggle"]
        }

        if debug_mode:
            print(f"开关状态: {active_categories}")

        # 加载所有分类特征短语（无论开关状态）
        all_features = {
            cat: self.get_category_features(cat)
            for cat in active_categories.keys()
        }

        # 加载排除词
        exclude_words = self.load_features(self.FILE_PATHS["exclude"]) if kwargs["exclude_toggle"] else set()

        # 处理原始文本
        raw_tags = [t.strip() for t in re.split(r'[，,]+', kwargs["text_input"]) if t.strip()]
        unique_tags = list(OrderedDict.fromkeys(raw_tags))  # 顺序去重

        if debug_mode:
            print(f"原始标签: {', '.join(unique_tags)}")

        # 分类匹配逻辑
        tag_status = {}
        
        for tag in unique_tags:
            tag_lower = tag.lower()
            is_excluded = False

            # 排除检查
            for phrase in exclude_words:
                pattern = r'\b' + re.escape(phrase) + r'\b'
                if re.search(pattern, tag_lower):
                    is_excluded = True
                    if debug_mode:
                        print(f"[DEBUG] 标签 '{tag}' 被排除词 '{phrase}' 匹配")
                    break

            if is_excluded:
                tag_status[tag] = {'exact': set(), 'substring': set(), 'excluded': True}
                continue

            # 初始化匹配状态
            exact_matches = set()
            substring_matches = set()

            # 遍历所有分类进行匹配
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

        # 生成最终输出
        final_output = []
        for tag in unique_tags:
            status = tag_status[tag]
            
            if status['excluded']:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 被排除")
                continue
            
            # 检查是否有精确匹配到关闭的分类
            inactive_exact_cats = [cat for cat in status['exact'] if not active_categories[cat]]
            if inactive_exact_cats:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 被过滤（精确匹配关闭的分类: {', '.join(inactive_exact_cats)}）")
                continue

            # 检查是否有子串匹配到关闭的分类
            inactive_substring_cats = [cat for cat in status['substring'] if not active_categories[cat]]
            if inactive_substring_cats:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 被过滤（子串匹配关闭的分类: {', '.join(inactive_substring_cats)}）")
                continue

            # 检查是否有开启的精确匹配
            active_exact_cats = [cat for cat in status['exact'] if active_categories[cat]]
            if active_exact_cats:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 被保留（精确匹配开启的分类: {', '.join(active_exact_cats)}）")
                final_output.append(tag)
                continue

            # 检查是否有开启的子串匹配
            active_substring_cats = [cat for cat in status['substring'] if active_categories[cat]]
            if active_substring_cats:
                if debug_mode:
                    print(f"[DEBUG] 标签 '{tag}' 被保留（子串匹配开启的分类: {', '.join(active_substring_cats)}）")
                final_output.append(tag)
                continue
            
            # 未匹配任何条件则保留
            if debug_mode:
                print(f"[DEBUG] 标签 '{tag}' 未匹配任何过滤词，被保留")
            final_output.append(tag)

        if debug_mode:
            print(f"过滤后标签: {', '.join(final_output)}")
            print("=== 过滤处理完成 ===\n")

        return (", ".join(final_output), )    
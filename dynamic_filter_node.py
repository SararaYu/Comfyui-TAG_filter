import re

class DynamicTextFilterNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_input": ("STRING", {"placeholder": "在此输入文本，用逗号分隔"}),  # 输入的文本
                "character_features": ("STRING", {"placeholder": "角色特征过滤词，用逗号分隔"}),
                "character_toggle": ("INT", {"default": 1, "min": 0, "max": 1}),  # 整数类型的开关
                "clothing_features": ("STRING", {"placeholder": "服装类过滤词，用逗号分隔"}),
                "clothing_toggle": ("INT", {"default": 1, "min": 0, "max": 1}),  # 整数类型的开关
                "custom1_features": ("STRING", {"placeholder": "自定义1过滤词，用逗号分隔"}),
                "custom1_toggle": ("INT", {"default": 1, "min": 0, "max": 1}),  # 整数类型的开关
                "custom2_features": ("STRING", {"placeholder": "自定义2过滤词，用逗号分隔"}),
                "custom2_toggle": ("INT", {"default": 1, "min": 0, "max": 1}),  # 整数类型的开关
                "custom3_features": ("STRING", {"placeholder": "自定义3过滤词，用逗号分隔"}),
                "custom3_toggle": ("INT", {"default": 1, "min": 0, "max": 1}),  # 整数类型的开关
                "exclude_features": ("STRING", {"placeholder": "排除的过滤词，用逗号分隔"})  # 排除标签输入项
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("总输出", "角色特征", "服装类", "自定义1", "自定义2", "自定义3", "其他")
    FUNCTION = "apply_filter"
    
    def apply_filter(self, text_input, character_features="", character_toggle=1, clothing_features="", clothing_toggle=1, custom1_features="", custom1_toggle=1, custom2_features="", custom2_toggle=1, custom3_features="", custom3_toggle=1, exclude_features=""):
        """根据过滤清单处理输入文本"""
        
        def parse_features(features):
            # 支持带引号和不带引号的标签，并去除空格，识别中文逗号和英文逗号
            return [feature.strip().strip('\'"') for feature in re.split(r'[，,]\s*(?=(?:[^\'"]*\'[^\'"]*\')*[^\'"]*$)', features) if feature.strip()]
        
        character_features_list = parse_features(character_features)
        clothing_features_list = parse_features(clothing_features)
        custom1_features_list = parse_features(custom1_features)
        custom2_features_list = parse_features(custom2_features)
        custom3_features_list = parse_features(custom3_features)
        exclude_features_list = parse_features(exclude_features)
        
        tags = [tag.strip() for tag in re.split(r'[，,]', text_input) if tag.strip()]
        
        # 排除包含排除标签的结果
        tags = [tag for tag in tags if not any(exclude in tag for exclude in exclude_features_list)]
        
        character_tags = [tag for tag in tags if any(feature in tag for feature in character_features_list)]
        clothing_tags = [tag for tag in tags if any(feature in tag for feature in clothing_features_list)]
        custom1_tags = [tag for tag in tags if any(feature in tag for feature in custom1_features_list)]
        custom2_tags = [tag for tag in tags if any(feature in tag for feature in custom2_features_list)]
        custom3_tags = [tag for tag in tags if any(feature in tag for feature in custom3_features_list)]
        
        filtered_tags = set(character_tags + clothing_tags + custom1_tags + custom2_tags + custom3_tags)
        other_tags = [tag for tag in tags if tag not in filtered_tags]
        
        total_output = ", ".join(tags)
        
        return (
            total_output,
            ", ".join(character_tags) if character_toggle else "",
            ", ".join(clothing_tags) if clothing_toggle else "",
            ", ".join(custom1_tags) if custom1_toggle else "",
            ", ".join(custom2_tags) if custom2_toggle else "",
            ", ".join(custom3_tags) if custom3_toggle else "",
            ", ".join(other_tags)
        )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Excel文档处理器
专门处理Excel文件，智能拼接关键字段生成描述性文本
"""

import re
import logging
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
from .legacy_processor import LegacyDocumentProcessor

logger = logging.getLogger(__name__)


class ExcelProcessor(LegacyDocumentProcessor):
    """专门的Excel文档处理器"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config or {})
        self.excel_config = self._init_excel_config()
        
    def _init_excel_config(self) -> Dict:
        """初始化Excel处理配置"""
        return {
            'max_rows_per_chunk': self.config.get('max_rows_per_chunk', 100),
            'min_rows_per_chunk': self.config.get('min_rows_per_chunk', 10),
            'include_headers': self.config.get('include_headers', True),
            'generate_descriptions': self.config.get('generate_descriptions', True),
            'smart_field_detection': self.config.get('smart_field_detection', True),
            'key_field_patterns': self.config.get('key_field_patterns', [
                r'名称|name|title|标题',
                r'描述|description|desc|说明',
                r'类型|type|category|分类',
                r'状态|status|state|状态',
                r'日期|date|time|时间',
                r'金额|price|cost|费用',
                r'数量|quantity|amount|数量',
                r'编号|id|code|编号',
                r'地址|address|location|位置',
                r'联系人|contact|person|人员'
            ]),
            'value_formatting': self.config.get('value_formatting', True)
        }
    
    def can_process(self, file_path: str) -> bool:
        """检查是否可以处理此文件"""
        return file_path.lower().endswith(('.xlsx', '.xls', '.csv'))
    
    def extract_text(self, file_path: str) -> str:
        """提取Excel文件文本内容"""
        try:
            if file_path.lower().endswith('.csv'):
                return self._process_csv_file(file_path)
            else:
                return self._process_excel_file(file_path)
        except Exception as e:
            logger.error(f"Excel文件处理失败: {e}")
            return ""
    
    def _process_excel_file(self, file_path: str) -> str:
        """处理Excel文件"""
        try:
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            all_content = []
            
            for sheet_name in sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    if not df.empty:
                        sheet_content = self._process_dataframe(df, sheet_name)
                        all_content.append(sheet_content)
                except Exception as e:
                    logger.warning(f"处理工作表 {sheet_name} 失败: {e}")
                    continue
            
            return "\n\n".join(all_content)
            
        except Exception as e:
            logger.error(f"Excel文件读取失败: {e}")
            return ""
    
    def _process_csv_file(self, file_path: str) -> str:
        """处理CSV文件"""
        try:
            df = pd.read_csv(file_path)
            if not df.empty:
                return self._process_dataframe(df, "CSV数据")
            return ""
        except Exception as e:
            logger.error(f"CSV文件读取失败: {e}")
            return ""
    
    def _process_dataframe(self, df: pd.DataFrame, sheet_name: str) -> str:
        """处理DataFrame，生成结构化文本"""
        if df.empty:
            return f"工作表: {sheet_name}\n(空数据)"
        
        # 清理数据
        df_clean = self._clean_dataframe(df)
        
        # 检测关键字段
        key_fields = self._detect_key_fields(df_clean) if self.excel_config['smart_field_detection'] else []
        
        # 生成描述性文本
        if self.excel_config['generate_descriptions']:
            description = self._generate_sheet_description(df_clean, sheet_name, key_fields)
        else:
            description = f"工作表: {sheet_name}\n"
        
        # 生成结构化内容
        content = self._generate_structured_content(df_clean, sheet_name, key_fields)
        
        return f"{description}\n{content}"
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理DataFrame数据"""
        # 删除全空的行和列
        df_clean = df.dropna(how='all').dropna(axis=1, how='all')
        
        # 填充空值
        df_clean = df_clean.fillna('')
        
        # 清理数据类型
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].astype(str).str.strip()
        
        return df_clean
    
    def _detect_key_fields(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """智能检测关键字段"""
        key_fields = []
        
        for col in df.columns:
            col_str = str(col).lower()
            field_info = {
                'column': col,
                'type': 'unknown',
                'importance': 0,
                'patterns': []
            }
            
            # 检测字段类型和重要性
            for pattern in self.excel_config['key_field_patterns']:
                if re.search(pattern, col_str, re.IGNORECASE):
                    field_info['patterns'].append(pattern)
                    field_info['importance'] += 1
            
            # 分析字段内容特征
            if not df[col].empty:
                sample_values = df[col].dropna().head(10)
                field_info.update(self._analyze_field_content(sample_values, col))
            
            if field_info['importance'] > 0 or field_info['type'] != 'unknown':
                key_fields.append(field_info)
        
        # 按重要性排序
        key_fields.sort(key=lambda x: x['importance'], reverse=True)
        return key_fields
    
    def _analyze_field_content(self, values: pd.Series, column_name: str) -> Dict[str, Any]:
        """分析字段内容特征"""
        analysis = {
            'type': 'unknown',
            'unique_count': values.nunique(),
            'has_numbers': any(re.search(r'\d', str(v)) for v in values),
            'has_dates': any(self._is_date_like(str(v)) for v in values),
            'avg_length': values.str.len().mean() if values.str.len().sum() > 0 else 0
        }
        
        # 推断字段类型
        if analysis['has_dates']:
            analysis['type'] = 'date'
        elif analysis['has_numbers'] and analysis['unique_count'] > 5:
            analysis['type'] = 'numeric'
        elif analysis['avg_length'] > 20:
            analysis['type'] = 'text'
        elif analysis['unique_count'] <= 10:
            analysis['type'] = 'categorical'
        
        return analysis
    
    def _is_date_like(self, value: str) -> bool:
        """判断字符串是否像日期"""
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{4}年\d{2}月\d{2}日',
            r'\d{2}月\d{2}日',
            r'\d{2}:\d{2}:\d{2}'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, value):
                return True
        return False
    
    def _generate_sheet_description(self, df: pd.DataFrame, sheet_name: str, key_fields: List[Dict]) -> str:
        """生成工作表描述"""
        description_parts = [f"工作表: {sheet_name}"]
        
        # 基本信息
        description_parts.append(f"总行数: {len(df)}")
        description_parts.append(f"总列数: {len(df.columns)}")
        
        # 关键字段信息
        if key_fields:
            description_parts.append("关键字段:")
            for field in key_fields[:5]:  # 只显示前5个关键字段
                field_desc = f"  - {field['column']}"
                if field['type'] != 'unknown':
                    field_desc += f" ({field['type']})"
                if field['patterns']:
                    field_desc += f" [匹配: {', '.join(field['patterns'][:2])}]"
                description_parts.append(field_desc)
        
        # 数据概览
        if len(df) > 0:
            sample_data = df.head(3)
            description_parts.append("数据预览:")
            for idx, row in sample_data.iterrows():
                row_desc = f"  行{idx+1}: "
                if key_fields:
                    # 显示关键字段的值
                    key_values = []
                    for field in key_fields[:3]:
                        if field['column'] in row:
                            value = str(row[field['column']])
                            if value and value != 'nan':
                                key_values.append(f"{field['column']}={value}")
                    if key_values:
                        row_desc += " | ".join(key_values)
                    else:
                        row_desc += " | ".join(str(v) for v in row.head(3) if str(v) != 'nan')
                else:
                    row_desc += " | ".join(str(v) for v in row.head(3) if str(v) != 'nan')
                description_parts.append(row_desc)
        
        return "\n".join(description_parts)
    
    def _generate_structured_content(self, df: pd.DataFrame, sheet_name: str, key_fields: List[Dict]) -> str:
        """生成结构化内容"""
        if df.empty:
            return "无数据内容"
        
        content_parts = []
        
        # 表头
        if self.excel_config['include_headers']:
            headers = [str(col) for col in df.columns]
            content_parts.append("列标题: " + " | ".join(headers))
            content_parts.append("")
        
        # 数据行
        for idx, row in df.iterrows():
            row_content = self._format_row_content(row, key_fields, idx)
            content_parts.append(row_content)
            
            # 添加分隔符
            if (idx + 1) % 50 == 0:  # 每50行添加分隔符
                content_parts.append("--- 数据分割线 ---")
        
        return "\n".join(content_parts)
    
    def _format_row_content(self, row: pd.Series, key_fields: List[Dict], row_idx: int) -> str:
        """格式化行内容"""
        if key_fields:
            # 优先显示关键字段
            key_values = []
            other_values = []
            
            for field in key_fields:
                if field['column'] in row:
                    value = str(row[field['column']])
                    if value and value != 'nan':
                        key_values.append(f"{field['column']}: {value}")
            
            # 其他字段
            for col in row.index:
                if col not in [f['column'] for f in key_fields]:
                    value = str(row[col])
                    if value and value != 'nan':
                        other_values.append(f"{value}")
            
            # 组合内容
            if key_values:
                row_content = f"行{row_idx+1}: {' | '.join(key_values)}"
                if other_values:
                    row_content += f" | 其他: {' | '.join(other_values[:3])}"  # 只显示前3个其他值
            else:
                row_content = f"行{row_idx+1}: {' | '.join(other_values[:5])}"  # 显示前5个值
        else:
            # 没有关键字段，显示所有值
            values = [str(v) for v in row if str(v) != 'nan']
            row_content = f"行{row_idx+1}: {' | '.join(values[:5])}"  # 显示前5个值
        
        return row_content

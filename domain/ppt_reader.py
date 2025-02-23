from typing import Dict, List
import json
from pptx.enum.dml import MSO_COLOR_TYPE, MSO_FILL
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pprint import pprint, pformat
from pathlib import Path
class PPTReader:
    @staticmethod  
    def __check_recursively_for_text(shape, text_list):
        for cur_shape in shape.shapes:
            if cur_shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                PPTReader.__check_recursively_for_text(cur_shape, text_list)
            else:
                if hasattr(cur_shape, "text"):
                    text_list.append(cur_shape.text)
        return text_list

    def _get_shape_infos(slide_number: int, shape: Dict) -> Dict:

        shape_details: Dict =  {
            "shape": {
                "slide_number": slide_number,

            }
        }
        if hasattr(shape, 'left') and hasattr(shape, 'right'): 
            shape_details["shape"]["position"] = {
                    "from_left": shape.left,
                    "from_top": shape.top
            }

        if hasattr(shape, 'width') and hasattr(shape, 'height'): 
            shape_details["shape"]["size"] = {
                    "width (EMU)": shape.width,
                    "height (EMU)": shape.height
            }

        if hasattr(shape, 'rotation'): 
            shape_details["shape"]["rotation_degrees"] = shape.rotation,
        shape_details["shape"]["shape_fore_color"] = "Transparent"

        if hasattr(shape, 'fill'):
            if shape.fill.type == MSO_FILL.SOLID:
                if shape.fill.fore_color.type == MSO_COLOR_TYPE.SCHEME:
                    shape_details["shape"]["shape_fore_color"] = f'Scheme color: {shape.fill.fore_color.theme_color}'
                elif shape.fill.fore_color.type == MSO_COLOR_TYPE.RGB:
                    shape_details["shape"]["shape_fore_color"] = f'(R, G, B): {shape.fill.fore_color.rgb}'
                else:
                    shape_details["shape"]["shape_fore_color"] = "Transparent"
        #else: print("No fore_color")

        if hasattr(shape, 'line'):
            line_style: Dict = {}
            line_fill = shape.line.fill
            if line_fill.type == MSO_FILL.SOLID:
                line_color = line_fill.fore_color
                if line_color.type == MSO_COLOR_TYPE.SCHEME:
                    line_style["line_color"] =  f'Scheme color: {line_color.theme_color}'
                elif line_color.type == MSO_COLOR_TYPE.RGB:
                    line_style["line_color"] = f'Hexadecimal:RRGGBB: {line_color.rgb}'
                else:
                    line_style["line_color"] = "Transparent"

            if hasattr(shape.line, "width"):
                line_style["line_width_points"] = shape.line.width.pt
            shape_details["shape"]["line"] = line_style

        if hasattr(shape, 'text_frame'):
            text_style: List = []
            for paragraph in shape.text_frame.paragraphs:
                font_details: Dict = {}
                for run in paragraph.runs:
                    font_details["font_name"] = run.font.name
                    font_details["font_size (PT)"] = run.font.size.pt if run.font.size is not None else "Not defined"
                    font_details["text_impacted"] = run.text
                    if run.font.color.type == MSO_COLOR_TYPE.SCHEME:
                        font_details["text_color"] =  f'Scheme color: {run.font.color.theme_color}'
                    elif run.font.color.type == MSO_COLOR_TYPE.RGB:
                        font_details["text_color"] = f'Hexadecimal:RRGGBB: {run.font.color.rgb}'
                    else:
                        font_details["text_color"] = "None"           
                    text_style.append(font_details)    
            shape_details["shape"]["font_details"] = text_style
            shape_details["shape"]["text"] = shape.text_frame.text

        return shape_details
    
    def __encapsulate_shape(shape: Dict, text: str, json_shape: Dict) -> Dict:
        new_json = json_shape.copy()
        new_json ["shape"]["type"] = str(shape.shape_type)
        return {
            'y': shape.top, 'x': shape.left, 
            'json': new_json,
            'raw_text': str(new_json["shape"]["text"]) if text is None else text
        }
    def get_text_box_info(slide_number: int, shape: Dict) -> Dict:
        json_shape: Dict = PPTReader._get_shape_infos(slide_number, shape)
        json_shape["shape"]["type"] = str(MSO_SHAPE_TYPE.TEXT_BOX)
        json_shape["shape"]["is_title"] = "False"
        return PPTReader.__encapsulate_shape(shape, None, json_shape)
    
    def get_group_info(slide_number: int, shape: Dict) -> Dict:
        json_shape: Dict = PPTReader._get_shape_infos(slide_number, shape)
        text_list: list = []
        text: str = "\n".join(PPTReader.__check_recursively_for_text(shape, text_list))
        return PPTReader.__encapsulate_shape(shape, text, json_shape)
    
    def get_table_info(slide_number: int, shape: Dict, table: Dict, table_elements: List, table_str: str) -> Dict:
        json_shape: Dict = PPTReader._get_shape_infos(slide_number, shape)
        json_shape["shape"]["table_size"] = {
             "number_cols": len(table.rows[0].cells),
             "number_rowss": len(table.rows)
        }
        json_shape["shape"]["mytype"] = "table"
        json_shape["shape"]["table_cells"] = [ element for element in table_elements]

        return PPTReader.__encapsulate_shape(shape, table_str, json_shape)

    def get_shape_type_info(slide_number: int, shape: Dict) -> Dict:
        json_shape: Dict = PPTReader._get_shape_infos(slide_number, shape)
        json_shape["shape"]["type"] = "shape_type"
        text: str = ""
        if "text" in json_shape["shape"].keys():
            text = json_shape["shape"]["text"]

        return PPTReader.__encapsulate_shape(shape, text, json_shape)

    def create_title(slide_number: int, title_value: str) -> Dict:
        shape: Dict = {
            'left': 0,
            'right': 0,            
            'width': len(title_value),
            'height': 10,
        }
        json_shape: Dict = PPTReader._get_shape_infos(slide_number, shape)
        json_shape["shape"]["type"] = str(MSO_SHAPE_TYPE.TEXT_BOX)
        json_shape["shape"]["is_title"] = "True"
        json_shape["shape"]["text"] = title_value
        return PPTReader.__encapsulate_shape(shape, title_value, json_shape)


    def get_sorted_shapes_by_pos_y(shapes: List) -> List:
        return sorted(shapes, key = lambda shape_dict: shape_dict['y'])


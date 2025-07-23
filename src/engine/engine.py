def convert_xyxy_to_xywh(box):
    '''
    Convert bounding box from xyxy format to xywh format.
    box: [x1, y1, x2, y2]
    return: [x_center, y_center, width, height]
    '''
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    x_center = x1 + width / 2
    y_center = y1 + height / 2
    return [x_center, y_center, width, height]
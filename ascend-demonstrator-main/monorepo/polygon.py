from shapely.geometry import Polygon

polygon_wkts = {
    "PLYTYPE_120_1": Polygon([(222, 100), (414, 100), (414, 40), (606, 40), (606, 100),
                              (798, 100), (798, 40), (990, 40), (990, 540), (798, 540),
                              (798, 480), (606, 480), (606, 540), (414, 540), (414, 480),
                              (222, 480), (222, 540), (30, 540), (30, 40), (222, 40)]),
    "PLYTYPE_120_2": Polygon([(1212, 100), (1404, 100), (1404, 40), (1596, 40), (1596, 100),
                              (1788, 100), (1788, 40), (1980, 40), (1980, 540), (1788, 540),
                              (1788, 480), (1596, 480), (1596, 540), (1404, 540), (1404, 480),
                              (1212, 480), (1212, 540), (1020, 540), (1020, 40), (1212, 40)]),
    "PLYTYPE_121_1": Polygon([(232, 100), (424, 100), (424, 40), (616, 40), (616, 100),
                              (808, 100), (808, 40), (1000, 40), (1000, 540), (808, 540),
                              (808, 480), (616, 480), (616, 540), (424, 540), (424, 480),
                              (232, 480), (232, 540), (40, 540), (40, 40), (232, 40)]),
    "PLYTYPE_121_2": Polygon([(1222, 100), (1414, 100), (1414, 40), (1606, 40), (1606, 100),
                              (1798, 100), (1798, 40), (1990, 40), (1990, 540), (1798, 540),
                              (1798, 480), (1606, 480), (1606, 540), (1414, 540), (1414, 480),
                              (1222, 480), (1222, 540), (1030, 540), (1030, 40), (1222, 40)]),
}

def calculate_polygon_metrics(polygon_dict):
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    for name, polygon in polygon_dict.items():
        if isinstance(polygon, Polygon):
            x, y = polygon.exterior.xy
            min_x = min(min_x, min(x))
            max_x = max(max_x, max(x))
            min_y = min(min_y, min(y))
            max_y = max(max_y, max(y))

    length_offset = 100  
    frame_width = max_x + length_offset
    frame_height = 1300
    general_frame_area = frame_width * frame_height

    total_ply_area = 0.0
    total_perimeter = 0.0
    ply_area_ratios = {}
    ply_perimeter_ratios = {}
    ply_wastages = {}
    ply_surface_areas = {}

    for name, polygon in polygon_dict.items():
        if isinstance(polygon, Polygon):
            ply_area = polygon.area
            ply_perimeter = polygon.length
            total_ply_area += ply_area
            total_perimeter += ply_perimeter
            ply_surface_areas[name] = ply_area  # Store individual ply surface area

    total_wastage = general_frame_area - total_ply_area

    for name, polygon in polygon_dict.items():
        if isinstance(polygon, Polygon):
            ply_area = polygon.area
            ply_perimeter = polygon.length

            ply_area_ratio = ply_area / total_ply_area if total_ply_area > 0 else 0
            ply_perimeter_ratio = ply_perimeter / total_perimeter if total_perimeter > 0 else 0

            ply_area_ratios[name] = ply_area_ratio
            ply_perimeter_ratios[name] = ply_perimeter_ratio

            wastage_A = total_wastage * ply_area_ratio if total_wastage > 0 else 0
            ply_wastages[name] = wastage_A

    return {
        "total_ply_area": total_ply_area,
        "total_perimeter": total_perimeter,
        "total_wastage": total_wastage,
        "ply_area_ratios": ply_area_ratios,
        "ply_perimeter_ratios": ply_perimeter_ratios,
        "ply_wastages": ply_wastages,
        "ply_surface_areas": ply_surface_areas,  # Include surface areas
        "general_frame_area": general_frame_area,
        "frame_width": frame_width,
        "frame_height": frame_height,
    }
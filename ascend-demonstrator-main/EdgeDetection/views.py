import os
import math
import json
import logging
import traceback

# Django imports
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Third-party library imports
import ezdxf
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Configure logging
logger = logging.getLogger(__name__)

def transform_point(point, offset=(0, 0), scale=(1, 1), rotation=0):
    try:
        # Handle different point input formats
        if hasattr(point, 'x') and hasattr(point, 'y'):
            x, y = point.x, point.y
        elif isinstance(point, (tuple, list)) and len(point) >= 2:
            x, y = point[0], point[1]
        elif hasattr(point, 'dxf') and hasattr(point.dxf, 'x') and hasattr(point.dxf, 'y'):
            x, y = point.dxf.x, point.dxf.y
        else:
            logger.warning(f"Unsupported point type: {type(point)}")
            return [0, 0]

        # Default scale to 1 if not provided or invalid
        sx = scale[0] if scale and len(scale) > 0 else 1
        sy = scale[1] if scale and len(scale) > 1 else sx

        # Apply scale
        x *= sx
        y *= sy

        # Apply rotation
        if rotation:
            angle = math.radians(rotation)
            x_rot = x * math.cos(angle) - y * math.sin(angle)
            y_rot = x * math.sin(angle) + y * math.cos(angle)
            x, y = x_rot, y_rot

        # Apply offset
        x += offset[0]
        y += offset[1]

        return [x, y]
    
    except Exception as e:
        logger.error(f"Error transforming point: {str(e)}")
        logger.error(traceback.format_exc())
        return [0, 0]

def process_dxf_entity(entity, doc, offset=(0, 0), scale=(1, 1), rotation=0):
    try:
        entity_type = entity.dxftype()
        logger.info(f"Processing entity type: {entity_type}")

        # Common processing for line-like entities
        if entity_type == 'LINE':
            try:
                start = transform_point(entity.dxf.start, offset, scale, rotation)
                end = transform_point(entity.dxf.end, offset, scale, rotation)
                return {
                    'type': 'line',
                    'points': [start, end]
                }
            except Exception as line_error:
                logger.error(f"Error processing LINE: {line_error}")
                return None
        
        # Handle LWPOLYLINE and POLYLINE
        elif entity_type in ['LWPOLYLINE', 'POLYLINE']:
            points = []
            try:
                if hasattr(entity, 'get_points'):
                    for p in entity.get_points():
                        points.append(transform_point(p, offset, scale, rotation))
                else:
                    for v in entity.vertices():
                        points.append(transform_point(v, offset, scale, rotation))
                
                return {
                    'type': 'polyline',
                    'points': points,
                    'closed': entity.dxf.flags & 1 == 1 if hasattr(entity, 'dxf') else False
                }
            except Exception as poly_error:
                logger.error(f"Error processing {entity_type}: {poly_error}")
                return None
        
        # Processing for CIRCLE entities
        elif entity_type == 'CIRCLE':
            try:
                center = transform_point(entity.dxf.center, offset, scale, rotation)
                radius = entity.dxf.radius * max(scale)
                
                # Generate points for circle
                points = [
                    [
                        center[0] + radius * math.cos(angle),
                        center[1] + radius * math.sin(angle)
                    ]
                    for angle in [2 * math.pi * i / 32 for i in range(33)]
                ]
                
                return {
                    'type': 'circle',
                    'points': points,
                    'center': center,
                    'radius': radius
                }
            except Exception as circle_error:
                logger.error(f"Error processing CIRCLE: {circle_error}")
                return None
        
        # Processing for ARC entities
        elif entity_type == 'ARC':
            try:
                center = transform_point(entity.dxf.center, offset, scale, rotation)
                radius = entity.dxf.radius * max(scale)
                
                start_angle = math.radians(entity.dxf.start_angle)
                end_angle = math.radians(entity.dxf.end_angle)
                
                # Ensure correct arc direction
                if end_angle < start_angle:
                    end_angle += 2 * math.pi
                
                # Generate points for arc
                points = [
                    [
                        center[0] + radius * math.cos(start_angle + (end_angle - start_angle) * t),
                        center[1] + radius * math.sin(start_angle + (end_angle - start_angle) * t)
                    ]
                    for t in [i / 32 for i in range(33)]
                ]
                
                return {
                    'type': 'arc',
                    'points': points,
                    'center': center,
                    'radius': radius,
                    'startAngle': entity.dxf.start_angle,
                    'endAngle': entity.dxf.end_angle
                }
            except Exception as arc_error:
                logger.error(f"Error processing ARC: {arc_error}")
                return None
        
        # Ellipse processing
        elif entity_type == 'ELLIPSE':
            try:
                center = transform_point(entity.dxf.center, offset, scale, rotation)
                major_axis = entity.dxf.major_axis
                ratio = entity.dxf.ratio
                
                points = [
                    [
                        center[0] + major_axis.x * math.cos(angle),
                        center[1] + major_axis.y * ratio * math.sin(angle)
                    ]
                    for angle in [2 * math.pi * i / 32 for i in range(33)]
                ]
                
                return {
                    'type': 'ellipse',
                    'points': points,
                    'center': center
                }
            except Exception as ellipse_error:
                logger.error(f"Error processing ELLIPSE: {ellipse_error}")
                return None
        
        # Spline processing
        elif entity_type == 'SPLINE':
            try:
                points = []
                for point in entity.get_points():
                    points.append(transform_point(point, offset, scale, rotation))
                
                return {
                    'type': 'polyline',
                    'points': points,
                    'closed': getattr(entity, 'closed', False)
                }
            except Exception as spline_error:
                logger.error(f"Error processing SPLINE: {spline_error}")
                return None
        
        # Block Insert processing
        elif entity_type == 'INSERT':
            try:
                block = doc.blocks[entity.dxf.name]
                processed_shapes = []
                
                for block_entity in block:
                    shape = process_dxf_entity(block_entity, doc, offset, scale, rotation)
                    if shape:
                        processed_shapes.append(shape)
                
                return processed_shapes if processed_shapes else None
            except Exception as insert_error:
                logger.error(f"Error processing INSERT: {insert_error}")
                return None
        
        # Text processing
        elif entity_type == 'TEXT':
            try:
                position = transform_point(entity.dxf.insert, offset, scale, rotation)
                return {
                    'type': 'text',
                    'points': [position],
                    'text': entity.dxf.text,
                    'height': entity.dxf.height * max(scale)
                }
            except Exception as text_error:
                logger.error(f"Error processing TEXT: {text_error}")
                return None
        
        # Unhandled entity type
        else:
            logger.warning(f"Unhandled entity type: {entity_type}")
            return None
    
    except Exception as e:
        logger.error(f"Unexpected error processing {entity_type} entity: {str(e)}")
        logger.error(traceback.format_exc())
        return None

# views.py
import os
import base64

def edge_detection(request, id):
    # Path to your images in the results directory
    base_path = '/home/airborne_amot/results/'
    original_image_path = os.path.join(base_path, 'original_image.jpg')
    ed_image_path = os.path.join(base_path, 'output.jpg')

    # Read and encode images to base64
    original_image = ''
    ed_image = ''
    
    try:
        with open(original_image_path, 'rb') as img_file:
            original_image = base64.b64encode(img_file.read()).decode('utf-8')
        
        with open(ed_image_path, 'rb') as img_file:
            ed_image = base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error reading images: {e}")

    context = {
        'id': id,
        'uploaded_file_name': request.session.get('uploaded_file_name', 'No file selected'),
        'original_image': original_image,
        'ed_image': ed_image
    }
    
    return render(request, 'EdgeDetection/edge_detection.html', context)
    
def run_edge_detection(request):
    if request.method == 'POST':
        try:
            # Retrieve processing parameters
            tolerance = request.POST.get('tolerance', 1.0)
            material_type = request.POST.get('material_type', 'default')
            
            # Placeholder for actual edge detection logic
            logger.info(f"Running edge detection - Tolerance: {tolerance}, Material: {material_type}")
            
            # This is where you'd integrate your specific edge detection processing
            return JsonResponse({
                'status': 'success',
                'message': 'Edge detection processed',
                'results': {
                    'tolerance': tolerance,
                    'material_type': material_type
                }
            })
        
        except Exception as e:
            logger.error(f"Error in edge detection: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to run edge detection'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)# Standard Python imports
    
@csrf_exempt
def process_dxf(request):
    if request.method == 'POST':
        try:
            # Check if file is in request
            if 'dxf_file' not in request.FILES:
                logger.error("No file uploaded in request")
                return JsonResponse({'status': 'error', 'message': 'No file uploaded'}, status=400)
            
            # Get the uploaded file
            dxf_file = request.FILES['dxf_file']
            file_name = dxf_file.name
            logger.info(f"Processing DXF file: {file_name}")
            
            # Create temporary directory
            temp_dir = 'temp_dxf'
            os.makedirs(temp_dir, exist_ok=True)
            
            # Save file temporarily
            temp_path = os.path.join(temp_dir, file_name)
            with open(temp_path, 'wb') as destination:
                for chunk in dxf_file.chunks():
                    destination.write(chunk)
            
            try:
                # Parse the DXF file
                doc = ezdxf.readfile(temp_path)
                msp = doc.modelspace()
                shapes = []
                
                # Process each entity in the modelspace
                for entity in msp:
                    processed_shape = process_dxf_entity(entity, doc)
                    if processed_shape:
                        # Handle potential list of shapes from INSERT
                        if isinstance(processed_shape, list):
                            shapes.extend(processed_shape)
                        else:
                            shapes.append(processed_shape)
                
                logger.info(f"Processed {len(shapes)} total shapes")
                
                # Store in session
                request.session['dxf_shapes'] = shapes
                request.session['uploaded_file_name'] = file_name
                
                # Optional WebSocket broadcast
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        'edge_detection',
                        {
                            'type': 'dxf_shapes',
                            'shapes': shapes
                        }
                    )
                except Exception as ws_error:
                    logger.warning(f"WebSocket communication error: {ws_error}")

                return JsonResponse({
                    'status': 'success',
                    'message': f'Processed {len(shapes)} shapes',
                    'shapes': shapes
                })
            
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except ezdxf.DXFError as e:
            logger.error(f"DXF parsing error: {str(e)}")
            logger.error(traceback.format_exc())
            return JsonResponse({
                'status': 'error', 
                'message': f'Invalid DXF file: {str(e)}'
            }, status=400)
        
        except Exception as e:
            logger.error(f"Unexpected error processing DXF: {str(e)}")
            logger.error(traceback.format_exc())
            return JsonResponse({
                'status': 'error', 
                'message': f'Unexpected error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Invalid request method'
    }, status=405)

def file_upload_view(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            if 'file' not in request.FILES:
                return JsonResponse({'error': 'No file uploaded'}, status=400)
            
            file = request.FILES['file']
            
            # Optional file type validation
            if not file.name.lower().endswith(('.dxf', '.jpg', '.png', '.txt')):
                return JsonResponse({'error': 'Invalid file type'}, status=400)
            
            try:
                # Save the file
                file_path = default_storage.save(f'uploads/{file.name}', ContentFile(file.read()))
                
                return JsonResponse({
                    'status': 'success', 
                    'filename': file.name,
                    'path': file_path
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    return JsonResponse({'error': 'Authentication required'}, status=401)

def image_upload_view(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            if 'image' not in request.FILES:
                return JsonResponse({'error': 'No image uploaded'}, status=400)
            
            image = request.FILES['image']
            
            # Image file type validation
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
            if not any(image.name.lower().endswith(ext) for ext in allowed_extensions):
                return JsonResponse({'error': 'Invalid image file type'}, status=400)
            
            try:
                # Save the image
                image_path = default_storage.save(f'images/{image.name}', ContentFile(image.read()))
                
                return JsonResponse({
                    'status': 'success', 
                    'filename': image.name,
                    'path': image_path
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
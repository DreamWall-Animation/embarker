
from embarker.appinfos import VERSION
from embarker.decoder import VIDEO_EXTENSIONS, IMAGE_EXTENSIONS


def ensure_session_compatibility(data):
    if data['version'] == VERSION:
        return data

    if data['version'][0] < 2:
        containers = []
        for container_id, path, metadata in data['containers']:
            if path.lower().endswith(VIDEO_EXTENSIONS):
                containers.append({
                    'type': 'video',
                    'kwargs': {
                        'video_path': path,
                        'metadata': metadata or None,
                        'container_id': container_id}})
            elif path.lower().endswith(IMAGE_EXTENSIONS):
                containers.append({
                    'type': 'image',
                    'kwargs': {
                        'path_pattern': path,
                        'metadata': metadata or None,
                        'container_id': container_id}})
        data['containers'] = containers

    return data

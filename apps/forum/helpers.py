def forum_image_path(instance, filename):
    return 'cfidb/forum/{0}/{1}'.format(
        instance.id, 
        filename
    )
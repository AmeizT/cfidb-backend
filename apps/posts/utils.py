def post_images_path(instance, filename):
    return 'cfidb/posts/{0}/{1}'.format(
        instance.post.assembly.name, 
        filename
    )


def post_image_url(instance, filename):
    return 'posts/{0}/{1}'.format(instance.post.assembly.name, filename)
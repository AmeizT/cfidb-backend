def post_images_path(instance, filename):
    return 'posts/{0}/{1}'.format(instance.post.author.username, filename)


def post_image_url(instance, filename):
    return 'posts/{0}/{1}'.format(instance.post.author.username, filename)
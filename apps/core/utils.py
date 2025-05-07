def blog_image_url(instance, filename):
    return 'blog/{0}/{1}'.format(instance.created_at, filename)
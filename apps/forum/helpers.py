def forum_image_path(instance, filename):
    return 'cfidb/changelog/{0}/{1}'.format(
        instance.pk, 
        filename
    )

def changelog_image_url(instance, filename):
    return 'changelog/{0}/{1}'.format(instance.created_at, filename)
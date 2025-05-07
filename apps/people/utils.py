def member_avatar_url(instance, filename):
    return 'avatars/{0}/{1}'.format(instance.first_name, filename)
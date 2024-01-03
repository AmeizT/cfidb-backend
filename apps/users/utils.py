def avatarURL(instance, filename):
    return 'account/avatars/{0}/{1}'.format(instance.id, filename)


def user_avatar_url(instance, filename):
    return 'avatars/{0}/{1}'.format(instance.first_name, filename)
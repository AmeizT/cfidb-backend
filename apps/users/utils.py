def avatarURL(instance, filename):
    return 'account/avatars/{0}/{1}'.format(instance.id, filename)


def user_avatar_url(instance, filename):
    return 'user/avatar/{0}/{1}'.format(instance.username, filename)
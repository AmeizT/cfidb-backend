def avatarURL(instance, filename):
    return 'account/avatars/{0}/{1}'.format(instance.id, filename)
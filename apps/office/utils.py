def meeting_file_path(instance, filename):
    return 'cfidb/{0}/meetings/{1}/{2}'.format(
        instance.church.name, 
        instance.meeting.title, 
        filename
    )
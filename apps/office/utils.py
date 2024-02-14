def meeting_file_path(instance, filename):
    return 'cfidb/{0}/meetings/{1}/{2}'.format(
        instance.church.name, 
        instance.meeting.title, 
        filename
    )


def uploaded_circular_path(instance, filename):
    return 'cfidb/circular/{0}/{1}'.format( 
        instance.category,  
        filename
    )


def uploaded_strategy_path(instance, filename):
    return 'cfidb/strategy/{0}/{1}'.format(
        instance.assembly.name,   
        filename
    )
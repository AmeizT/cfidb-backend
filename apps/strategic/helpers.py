def strategy_file_path(instance, filename):
    return 'cfidb/strategy/{0}/{1}/{2}'.format(
        instance.branch.name,  
        instance.timestamp,  
        filename
    )


def strategy_banner_path(instance, filename):
    return 'cfidb/strategy/{0}/{1}/{2}'.format(
        instance.branch.name,  
        instance.created_at,  
        filename
    )
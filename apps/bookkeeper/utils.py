def asset_image_path(instance, filename):
    return 'cfidb/bookkeeper/{0}/assets/{1}'.format(
        instance.church.name, 
        filename
    )
    

def bank_statement_path(instance, filename):
    return 'cfidb/bookkeeper/{0}/income/{1}/{2}'.format(
        instance.church.name, 
        instance.timestamp, 
        filename
    )


def expenditure_receipt_path(instance, filename):
    return 'cfidb/bookkeeper/{0}/expenditure/{1}/{2}'.format(
        instance.church.name, 
        instance.invoice_date, 
        filename
    )
    
    
def fixed_expenditure_receipt_path(instance, filename):
    return 'cfidb/bookkeeper/{0}/expenditure/{1}/{2}'.format(
        instance.branch.name, 
        instance.timestamp, 
        filename
    )
    
    
def tithe_receipt_path(instance, filename):
    return 'cfidb/bookkeeper/{0}/tithes/{1}-{2}/{3}'.format(
        instance.branch.name, 
        instance.member.first_name, 
        instance.member.last_name, 
        filename
    )
    
    
def pledge_receipt_path(instance, filename):
    return 'cfidb/bookkeeper/{0}/pledges/{1}-{2}/{3}'.format(
        instance.branch.name, 
        instance.member.first_name, 
        instance.member.last_name, 
        filename
    )


def remittance_receipt_path(instance, filename):
    return 'cfidb/bookkeeper/{0}/remittances/{1}-{2}/'.format(
        instance.branch.name, 
        instance.timestamp, 
        filename
    )

def shortfall_receipt_path(instance, filename):
    return 'cfidb/bookkeeper/{0}/remit-shortfalls/{1}-{2}/'.format(
        instance.remittance.branch.name, 
        instance.timestamp,  
        filename
    )
    

from django.db import models

class Gender(models.TextChoices):
    MALE = 'Male', 'Male'
    FEMALE = 'Female', 'Female'


class MembershipStatus(models.TextChoices):
    VISITOR = 'visitor', 'Visitor'
    REGULAR = 'regular', 'Regular Attendee'
    ESTABLISHED = 'established', 'Established Member'
    INACTIVE = 'inactive', 'Inactive'
    TRANSFERRED = 'transferred', 'Transferred'
    DECEASED = 'deceased', 'Deceased'


class EducationLevel(models.TextChoices):
    PRIMARY = 'primary', 'Primary'
    SECONDARY = 'secondary', 'Secondary'
    DIPLOMA = 'diploma', 'Diploma'
    BACHELOR = 'bachelor', 'Bachelor\'s Degree'
    MASTER = 'master', 'Master\'s Degree'
    DOCTORATE = 'doctorate', 'Doctorate'
    OTHER = 'other', 'Other'
    

class AttendanceCategories(models.TextChoices):
    FRIDAY = 'friday', 'Friday'
    HOMECELL = 'homecell', 'Homecell'
    OUTREACH = 'outreach', 'Outreach'
    OTHER = 'other', 'Other'
    SUNDAY = 'sunday', 'Sunday'

class GuardianRelationship(models.TextChoices):
    AUNT = "Aunt", "Aunt"
    BROTHER = "Brother", "Brother"
    CHILD = "Child", "Child"
    COUSIN = "Cousin", "Cousin"
    FATHER = "Father", "Father"
    GRANDPARENT = "Grandparent", "Grandparent"
    MOTHER = "Mother", "Mother"
    SISTER = "Sister", "Sister"
    SPOUSE = "Spouse", "Spouse"
    UNCLE = "Uncle", "Uncle"


class Relationship(models.TextChoices):
    SINGLE = 'Single', 'Single'
    MARRIED = 'Married', 'Married'
    DIVORCED = 'Divorced', 'Divorced'
    WIDOWED = 'Widowed', 'Widowed'
    SEPARATED = 'Separated', 'Separated'
    ENGAGED = 'Engaged', 'Engaged'
    IN_A_RELATIONSHIP = 'In a Relationship', 'In a Relationship'
    DOMESTIC_PARTNERSHIP = 'Domestic Partnership', 'Domestic Partnership'
    CIVIL_UNION = 'Civil Union', 'Civil Union'
    COMMITTED = 'Committed', 'Committed'
    COMMON_LAW_MARRIAGE = 'Common-Law Marriage', 'Common-Law Marriage'
    TRADITIONAL_MARRIAGE = 'Traditional Marriage', 'Traditional Marriage'
    CO_PARENTING = 'Co-parenting', 'Co-parenting'


class Prefixes(models.TextChoices):
    ADV = 'Advocate', 'Advocate'
    DR = 'Dr', 'Dr'
    ENG = 'Eng', 'Eng'
    HON = 'Hon', 'Hon'
    MISS = 'Miss', 'Miss'
    MR = 'Mr', 'Mr'
    MRS = 'Mrs', 'Mrs'
    MS = 'Ms', 'Ms'
    PROF = 'Prof', 'Prof'
    REV = 'Rev', 'Rev'


class ChurchRoles(models.TextChoices):
    DEACON = 'Deacon', 'Deacon'
    DEACONESS = 'Deaconess', 'Deaconess'
    ELDER = 'Elder', 'Elder'
    GATEKEEPERS_LEADER = 'Gatekeepers Leader', 'Gatekeepers Leader'
    GENERAL_OVERSEER = 'General Overseer', 'General Overseer'
    HOUSE_KEEPER = 'House Keeper', 'House Keeper'
    HOME_CELL_LEADER = 'Home Cell Leader', 'Home Cell Leader'
    MEDIA_DIRECTOR = 'Media Director', 'Media Director'
    NATIONAL_OVERSEER = 'National Overseer', 'National Overseer'
    OTHER = 'Other', 'Other'
    PASTOR = 'Pastor', 'Pastor'
    PRAISE_AND_WORSHIP_DIRECTOR = 'Praise and Worship Director', 'Praise and Worship Director'
    PRESIDENT = 'President', 'President'
    SECRETARY = 'Secretary', 'Secretary'
    SECRETARY_GENERAL = 'Secretary General', 'Secretary General'
    SENIOR_PASTOR = 'Senior Pastor', 'Senior Pastor'
    SUNDAY_SCHOOL_TEACHER = 'Sunday School Teacher', 'Sunday School Teacher'
    TREASURER = 'Treasurer', 'Treasurer'
    USHER = 'Usher', 'Usher'
    WOE_LEADER = 'WOE Leader', 'WOE Leader'
    YOUTH_LEADER = 'Youth Leader', 'Youth Leader'


class Ministries(models.TextChoices):
    ADMINISTRATION = 'Administration', 'Administration'
    CHRISTIAN_EDUCATION = 'Christian Education', 'Christian Education'
    COUNSELING = 'Counseling', 'Counseling'
    DISCERNMENT = 'Discernment', 'Discernment'
    EVANGELISM = 'Evangelism', 'Evangelism'
    GIVING = 'Giving', 'Giving'
    HOSPITALITY = 'Hospitality', 'Hospitality'
    INTERCESSION = 'Intercession', 'Intercession'
    LEADERSHIP = 'Leadership', 'Leadership'
    MEDIA = 'Media and Communications', 'Media and Communications'
    OTHER = 'Other', 'Other'
    PRAISE_AND_WORSHIP = 'Praise and Worship', 'Praise and Worship'
    SUNDAY_SCHOOL = 'Sunday School', 'Sunday School'
    USHERING = 'Ushering', 'Ushering'
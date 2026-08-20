from django.db import models

class Gender(models.TextChoices):
    MALE = 'Male', 'Male'
    FEMALE = 'Female', 'Female'

class EducationLevel(models.TextChoices):
    PRIMARY = 'Primary', 'Primary'
    SECONDARY = 'Secondary', 'Secondary'
    DIPLOMA = 'Diploma', 'Diploma'
    BACHELOR = 'Bachelor\'s Degree', 'Bachelor\'s Degree'
    MASTER = 'Master\'s Degree', 'Master\'s Degree'
    DOCTORATE = 'Doctorate', 'Doctorate'
    OTHER = 'Other', 'Other'

class GuardianRelationship(models.TextChoices):
    AUNT = 'Aunt', 'Aunt'
    BROTHER = 'Brother', 'Brother'
    CHILD = 'Child', 'Child'
    COUSIN = 'Cousin', 'Cousin'
    FATHER = 'Father', 'Father'
    GRANDPARENT = 'Grandparent', 'Grandparent'
    MOTHER = 'Mother', 'Mother'
    SISTER = 'Sister', 'Sister'
    SPOUSE = 'Spouse', 'Spouse'
    UNCLE = 'Uncle', 'Uncle'

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



from django import forms
from django.contrib import admin
from apps.users.models import User, Profile, AuthHistory, DelegatePermission, Role
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField


class UserCreationForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput,
    )
    re_password = forms.CharField(
        label='Password again',
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'church')

    def clean_re_password(self):
        password = self.cleaned_data.get("password")
        re_password = self.cleaned_data.get("re_password")
        if password and re_password and password != re_password:
            raise forms.ValidationError("Passwords don't match")
        return re_password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ('email', 'password',)

    def clean_password(self):
        return self.initial["password"]


class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = [ 
        'first_name', 
        'last_name', 
        'username', 
        'email', 
        'last_login', 
        'created_at', 
        'updated_at',
    ]
    list_filter = (
        'church', 
        'is_admin', 
        'roles',
    )
    fieldsets = (
        ('Authentication', {
                'fields': ('email', 'password',)
            }
        ),
        ('Bio', {
            'fields': [
                'first_name', 
                'last_name', 
                'username', 
                'avatar', 
                'avatar_fallback',
            ]
        }),
        ('Workspace', {
            'fields': [
                'church', 
                'assemblies',
                'roles',
            ]
        }),
        ('Account Recovery', {
            'fields': [
                'recovery_email', 
            ]
        }),
        ('Permissions', {
            'fields': [
                'is_active', 
                'is_admin', 
                'is_staff',
                'is_db_staff',
                'is_db_zone_staff',
                'is_academy_staff',
                'is_superuser', 
                'is_onboarded', 
            ]
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'first_name', 
                'last_name', 
                'username', 
                'email', 
                'church', 
                'assemblies',
                'roles',
                'password', 
                're_password'
            ),
        }),
    )
    search_fields = ('email', 'username',)
    ordering = ()
    filter_horizontal = ()
    readonly_fields = (
        'is_db_staff',
        'is_db_zone_staff',
        'is_academy_staff',
        'is_staff',
    )

admin.site.register(User, UserAdmin)
admin.site.register(Profile)
admin.site.register(AuthHistory)
admin.site.register(DelegatePermission)
admin.site.register(Role)


from django import forms
from django.contrib import admin
from apps.users.models import User, Account
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
        'role',
        'last_login', 
        'created_at', 
        'updated_at',
    ]
    list_filter = (
        'church', 
        'is_admin', 
        'role',
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
                'church', 
                'churches',
                'role',
                'avatar', 
                'avatar_fallback',
            ]
        }),
        ('Permissions', {
            'fields': [
                'is_active', 
                'is_admin', 
                'is_superuser', 
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
                'churches',
                'role',
                'password', 
                're_password'
            ),
        }),
    )
    search_fields = ('email', 'username',)
    ordering = ()
    filter_horizontal = ()

admin.site.register(User, UserAdmin)
admin.site.register(Account)


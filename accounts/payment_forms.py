"""
Forms for managing payment details for owners and operators
"""

from django import forms
from django.contrib.auth.decorators import login_required
from .models import PaymentDetails, OperatorPaymentConfig


class OwnerPaymentDetailsForm(forms.ModelForm):
    """
    Form for owners to manage their payment details for receiving payouts.
    """
    
    class Meta:
        model = PaymentDetails
        fields = ['payment_method', 'account_identifier', 'account_holder_name', 
                  'bank_name', 'bank_branch', 'is_default']
        widgets = {
            'payment_method': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-all duration-200 shadow-sm',
            }),
            'account_identifier': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-all duration-200 shadow-sm',
                'placeholder': 'e.g., +255 123 456 789 or 12345-67890-123',
                'required': True,
            }),
            'account_holder_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-all duration-200 shadow-sm',
                'placeholder': 'Name on the account',
                'required': True,
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-all duration-200 shadow-sm',
                'placeholder': 'Bank name (if applicable)',
            }),
            'bank_branch': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-gray-300 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1a5c38]/30 focus:border-[#1a5c38] transition-all duration-200 shadow-sm',
                'placeholder': 'Branch name/code (if applicable)',
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 text-[#1a5c38] rounded border-gray-300 focus:ring-[#1a5c38]/30 transition-all cursor-pointer',
            }),
        }
        labels = {
            'payment_method': 'Payment Method',
            'account_identifier': 'Account Number / Phone Number',
            'account_holder_name': 'Account Holder Name',
            'bank_name': 'Bank Name',
            'bank_branch': 'Bank Branch',
            'is_default': 'Set as default payout method',
        }
        help_texts = {
            'account_identifier': 'The M-Pesa/Airtel number or bank account where you want to receive payouts',
            'account_holder_name': 'Full name associated with this payment account',
            'bank_name': 'Leave blank if using mobile money (M-Pesa, Airtel, Tigo)',
            'bank_branch': 'Leave blank if using mobile money',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_name'].required = False
        self.fields['bank_branch'].required = False

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        bank_name = cleaned_data.get('bank_name')
        account_identifier = cleaned_data.get('account_identifier')
        account_holder_name = cleaned_data.get('account_holder_name')

        if not account_identifier:
            raise forms.ValidationError('Account number or phone number is required.')
        
        if not account_holder_name:
            raise forms.ValidationError('Account holder name is required.')

        # For bank transfers, require bank details
        if payment_method == 'bank_transfer' and not bank_name:
            raise forms.ValidationError('Bank name is required for bank transfers.')

        return cleaned_data


class OperatorPaymentConfigForm(forms.ModelForm):
    """
    Form for admins to configure payment details for customers to pay.
    """
    
    class Meta:
        model = OperatorPaymentConfig
        fields = ['payment_method', 'account_identifier', 'account_holder_name', 
                  'bank_name', 'bank_branch', 'instructions', 'is_active', 'priority']
        widgets = {
            'payment_method': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary',
            }),
            'account_identifier': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary',
                'placeholder': 'e.g., +255 123 456 789 or 12345-67890-123',
                'required': True,
            }),
            'account_holder_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary',
                'placeholder': 'Business/Operator name',
                'required': True,
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary',
                'placeholder': 'Bank name (if applicable)',
            }),
            'bank_branch': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary',
                'placeholder': 'Branch name/code (if applicable)',
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary',
                'rows': 3,
                'placeholder': 'Payment instructions to display to customers',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded',
            }),
            'priority': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary',
                'min': '0',
                'placeholder': '0 for highest priority',
            }),
        }
        labels = {
            'payment_method': 'Payment Method',
            'account_identifier': 'Account Number / Phone Number',
            'account_holder_name': 'Business Name',
            'bank_name': 'Bank Name',
            'bank_branch': 'Bank Branch',
            'instructions': 'Payment Instructions',
            'is_active': 'Active (visible to customers)',
            'priority': 'Display Priority',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_name'].required = False
        self.fields['bank_branch'].required = False
        self.fields['instructions'].required = False

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        bank_name = cleaned_data.get('bank_name')

        # For bank transfers, require bank details
        if payment_method == 'bank_transfer' and not bank_name:
            raise forms.ValidationError('Bank name is required for bank transfers.')

        return cleaned_data

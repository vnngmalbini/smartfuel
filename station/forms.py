from django import forms
from .models import (
    FuelType, FuelInventory, Pump, Customer, Transaction, 
    FuelPriceHistory, Staff, StaffRole
)
from django.contrib.auth.models import User


class FuelPriceForm(forms.ModelForm):
    """Form for updating fuel prices"""
    class Meta:
        model = FuelType
        fields = ['current_price']
        widgets = {
            'current_price': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Enter new price',
                'step': '0.01',
                'min': '0',
            }),
        }


class FuelInventoryForm(forms.ModelForm):
    """Form for managing fuel inventory"""
    class Meta:
        model = FuelInventory
        fields = ['quantity_liters', 'min_threshold', 'max_capacity', 'cost_per_liter']
        widgets = {
            'quantity_liters': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Current quantity in liters',
                'step': '0.01',
            }),
            'min_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Minimum stock threshold',
                'step': '0.01',
            }),
            'max_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Maximum tank capacity',
                'step': '0.01',
            }),
            'cost_per_liter': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cost per liter',
                'step': '0.01',
            }),
        }


class PumpForm(forms.ModelForm):
    """Form for managing pumps"""
    class Meta:
        model = Pump
        fields = ['pump_number', 'fuel_type', 'status', 'meter_reading', 'installation_date', 'last_maintenance']
        widgets = {
            'pump_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., P-001',
            }),
            'fuel_type': forms.Select(attrs={
                'class': 'form-control form-select',
            }),
            'status': forms.Select(attrs={
                'class': 'form-control form-select',
            }),
            'meter_reading': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Current meter reading',
                'step': '0.01',
            }),
            'installation_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'last_maintenance': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
        }


class PumpMaintenanceForm(forms.ModelForm):
    """Form for pump maintenance records"""
    maintenance_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Maintenance details',
        }),
        required=False
    )
    
    class Meta:
        model = Pump
        fields = ['last_maintenance', 'meter_reading']
        widgets = {
            'last_maintenance': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'meter_reading': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Updated meter reading',
                'step': '0.01',
            }),
        }


class CustomerForm(forms.ModelForm):
    """Form for customer registration/update"""
    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'phone', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number',
                'type': 'tel',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address',
            }),
        }


class TransactionForm(forms.ModelForm):
    """Form for recording fuel transactions"""
    customer_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Customer phone (optional)',
            'type': 'tel',
        })
    )
    
    class Meta:
        model = Transaction
        fields = ['fuel_type', 'liters_dispensed', 'payment_method', 'notes']
        widgets = {
            'fuel_type': forms.Select(attrs={
                'class': 'form-control form-select',
            }),
            'liters_dispensed': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Liters to dispense',
                'step': '0.01',
                'min': '0.01',
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control form-select',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)',
            }),
        }


class StaffForm(forms.ModelForm):
    """Form for staff registration and management"""
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Staff
        fields = ['role', 'phone', 'national_id', 'date_hired', 'salary']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control form-select'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'tel',
                'placeholder': 'Phone number',
            }),
            'national_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'National ID',
            }),
            'date_hired': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Monthly salary',
                'step': '0.01',
            }),
        }


class TransactionFilterForm(forms.Form):
    """Form for filtering transactions"""
    FILTER_CHOICES = [
        ('', 'All Transactions'),
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile_money', 'Mobile Money'),
        ('paystack', 'Paystack'),
    ]
    
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=FILTER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-select'})
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )


class ReportsFilterForm(forms.Form):
    """Form for filtering reports"""
    DATE_RANGE_CHOICES = [
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('year', 'This Year'),
        ('custom', 'Custom Range'),
    ]
    
    date_range = forms.ChoiceField(
        choices=DATE_RANGE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control form-select'})
    )
    custom_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    custom_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )

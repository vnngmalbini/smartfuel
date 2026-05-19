from django.db.models import Sum
from station.models import Customer, Transaction

customers = Customer.objects.all()
print('Customers to update:', customers.count())
for c in customers:
    sums = Transaction.objects.filter(customer=c, status='completed').aggregate(total_amount=Sum('total_amount'), total_liters=Sum('liters_dispensed'))
    total_amount = sums.get('total_amount') or 0
    total_liters = sums.get('total_liters') or 0
    c.total_purchases = total_amount
    c.total_liters = total_liters
    c.save(update_fields=['total_purchases','total_liters'])
    print('Updated', c.phone, float(c.total_purchases), float(c.total_liters))

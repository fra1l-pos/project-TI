from django import forms
from .models import AnioAcademico, Pago

class AnioAcademicoForm(forms.ModelForm):
    class Meta:
        model = AnioAcademico
        fields = ['anio', 'pension_base']
        widgets = {
            'anio': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-colegio-500 focus:border-colegio-500'}),
            'pension_base': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-colegio-500 focus:border-colegio-500', 'step': '0.01'}),
        }


INPUT_CLASS = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-colegio-500 focus:border-colegio-500 sm:text-sm'


class PagoForm(forms.ModelForm):
    """
    Formulario para que el padre registre el pago de una pensión.
    Validaciones para minimizar errores:
    - El monto se precarga con la deuda y debe ser exacto (evita pagos parciales/erróneos).
    - El N° de operación/recibo y el comprobante son obligatorios para TODOS los métodos,
      incluido Efectivo (así ningún pago queda sin evidencia).
    """
    class Meta:
        model = Pago
        fields = ['monto_pagado', 'metodo_pago', 'numero_operacion', 'comprobante']
        labels = {
            'numero_operacion': 'N° de operación / recibo',
            'comprobante': 'Comprobante o recibo (Imagen/PDF)',
        }
        widgets = {
            'monto_pagado': forms.NumberInput(attrs={
                'class': INPUT_CLASS, 'step': '0.01', 'min': '0', 'inputmode': 'decimal',
            }),
            'metodo_pago': forms.Select(attrs={'class': INPUT_CLASS}),
            'numero_operacion': forms.TextInput(attrs={
                'class': INPUT_CLASS, 'placeholder': 'Ej: 990888123456 o N° de recibo',
            }),
            'comprobante': forms.ClearableFileInput(attrs={'class': INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        self.pension = kwargs.pop('pension', None)
        super().__init__(*args, **kwargs)
        if self.pension:
            self.fields['monto_pagado'].initial = self.pension.monto_deuda
            self.fields['monto_pagado'].help_text = f'Deuda registrada: S/ {self.pension.monto_deuda}'

    def clean_monto_pagado(self):
        monto = self.cleaned_data.get('monto_pagado')
        if monto is None or monto <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        if self.pension and monto != self.pension.monto_deuda:
            raise forms.ValidationError(
                f'El monto debe ser exactamente S/ {self.pension.monto_deuda}. '
                'Si deseas pagar otro monto, comunícate con el administrador.'
            )
        return monto

    def clean(self):
        cleaned_data = super().clean()
        numero = cleaned_data.get('numero_operacion')
        comprobante = cleaned_data.get('comprobante')

        # Todos los métodos (incluido Efectivo) requieren N° de operación/recibo y comprobante
        if not numero:
            self.add_error('numero_operacion', 'Ingresa el N° de operación o de recibo.')
        if not comprobante:
            self.add_error('comprobante', 'Sube el comprobante o el recibo (foto o PDF).')
        return cleaned_data

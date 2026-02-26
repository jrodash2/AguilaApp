from django import forms


class PadronUploadForm(forms.Form):
    archivo = forms.FileField(
        required=True,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".xlsx,.csv",
            }
        ),
        help_text="Solo se permiten archivos .xlsx o .csv",
    )
    replace = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "id_replace",
            }
        ),
        label="Reemplazar/Actualizar padrón existente",
    )

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if not archivo:
            raise forms.ValidationError("Debe seleccionar un archivo para continuar.")

        nombre = archivo.name.lower().strip()
        if not (nombre.endswith(".xlsx") or nombre.endswith(".csv")):
            raise forms.ValidationError("Formato inválido. Solo se permiten archivos .xlsx o .csv.")

        return archivo

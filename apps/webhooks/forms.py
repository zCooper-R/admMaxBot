from django import forms


class WebhookActionForm(forms.Form):
    webhook_url = forms.URLField(
        label="URL webhook",
        required=False,
        assume_scheme="https",
        widget=forms.URLInput(attrs={"placeholder": "https://example.gov/webhooks/max/"}),
    )

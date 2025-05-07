# beauty_app/mixins.py

class AuditableMixin:
    """
    A mixin for models to track field changes for auditing.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store initial state
        self._original_state = self._get_field_values()
        self._changed_fields = []
    
    def _get_field_values(self):
        """Get current field values as a dictionary, safely handling related fields."""
        field_values = {}
        
        for field in self._meta.fields:
            field_name = field.name
            
            # Skip password fields
            if field_name == 'password':
                continue
                
            try:
                # For foreign keys and relations, store the ID rather than trying to access the object
                if field.is_relation:
                    # Get the ID value directly from the field
                    field_id_name = f"{field_name}_id"
                    if hasattr(self, field_id_name):
                        field_values[field_name] = getattr(self, field_id_name)
                    else:
                        # Skip if the relation isn't set yet
                        continue
                else:
                    # For regular fields, get the value normally
                    field_values[field_name] = getattr(self, field_name)
            except (AttributeError, ValueError, TypeError):
                # Skip any field that raises an error when accessed
                continue
                
        return field_values
    
    def save(self, *args, **kwargs):
        if self.pk:  # Only check for changes on updates, not on creation
            current_state = self._get_field_values()
            self._changed_fields = [
                field_name for field_name, value in current_state.items()
                if self._original_state.get(field_name) != value
            ]
        
        # Call the parent save method
        result = super().save(*args, **kwargs)
        
        # Update the original state after saving
        self._original_state = self._get_field_values()
        self._changed_fields = []
        
        return result
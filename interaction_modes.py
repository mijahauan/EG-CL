#!/usr/bin/env python3
"""
Interaction modes for existential graph manipulation.
Defines different constraint levels and behaviors for various use cases.
"""

from enum import Enum, auto
from typing import Dict, Any, Optional, List
from PySide6.QtCore import QObject, Signal, QPointF

class InteractionMode(Enum):
    """Defines the different interaction modes for existential graph manipulation."""
    
    CONSTRAINED = auto()     # Rearrange existing well-formed expressions
    COMPOSITION = auto()     # Free-form construction of new graphs
    TRANSFORMATION = auto()  # Rule-based modifications following Peirce's rules

class ValidationLevel(Enum):
    """Defines different levels of validation strictness."""
    
    NONE = auto()           # No validation
    BASIC = auto()          # Basic structural validation
    STRICT = auto()         # Full logical validation
    RULE_BASED = auto()     # Peirce's transformation rules

class LigatureBindingMode(Enum):
    """Defines how ligatures behave when connected elements move."""
    
    RIGID = auto()          # Ligatures maintain connections rigidly
    FLEXIBLE = auto()       # Ligatures can stretch but maintain connections
    DETACHABLE = auto()     # Ligatures can detach when moved too far
    FREE = auto()           # Ligatures move independently

class InteractionModeManager(QObject):
    """Manages interaction modes and their associated behaviors."""
    
    # Signals for mode changes
    mode_changed = Signal(InteractionMode)
    validation_level_changed = Signal(ValidationLevel)
    
    def __init__(self):
        super().__init__()
        
        # Current mode settings
        self.current_mode = InteractionMode.COMPOSITION  # Default to most flexible
        self.validation_level = ValidationLevel.BASIC
        self.ligature_binding = LigatureBindingMode.FLEXIBLE
        
        # Mode configurations
        self.mode_configs = {
            InteractionMode.CONSTRAINED: {
                'validation_level': ValidationLevel.STRICT,
                'ligature_binding': LigatureBindingMode.RIGID,
                'allow_containment_violation': False,
                'allow_rule_violation': False,
                'auto_validate': True,
                'description': 'Constrained rearrangement of well-formed expressions'
            },
            InteractionMode.COMPOSITION: {
                'validation_level': ValidationLevel.BASIC,
                'ligature_binding': LigatureBindingMode.FLEXIBLE,
                'allow_containment_violation': True,
                'allow_rule_violation': True,
                'auto_validate': False,
                'description': 'Free-form construction with validation on demand'
            },
            InteractionMode.TRANSFORMATION: {
                'validation_level': ValidationLevel.RULE_BASED,
                'ligature_binding': LigatureBindingMode.RIGID,
                'allow_containment_violation': False,
                'allow_rule_violation': False,
                'auto_validate': True,
                'description': 'Rule-based modifications following Peirce\'s transformation rules'
            }
        }
        
    def set_mode(self, mode: InteractionMode):
        """Set the current interaction mode and update associated settings."""
        if mode != self.current_mode:
            old_mode = self.current_mode
            self.current_mode = mode
            
            # Update settings based on mode
            config = self.mode_configs[mode]
            self.validation_level = config['validation_level']
            self.ligature_binding = config['ligature_binding']
            
            print(f"Interaction mode changed from {old_mode} to {mode}")
            print(f"Description: {config['description']}")
            
            # Emit signals
            self.mode_changed.emit(mode)
            self.validation_level_changed.emit(self.validation_level)
            
    def get_mode(self) -> InteractionMode:
        """Get the current interaction mode."""
        return self.current_mode
        
    def get_config(self, key: str) -> Any:
        """Get a configuration value for the current mode."""
        return self.mode_configs[self.current_mode].get(key)
        
    def should_validate_movement(self, node_id: str, new_position: QPointF) -> bool:
        """Determine if movement should be validated based on current mode."""
        config = self.mode_configs[self.current_mode]
        
        # If auto_validate is False, don't validate
        if not config['auto_validate']:
            return False
            
        # If containment violations are allowed, don't validate containment
        # But we might still want other validations, so return True for now
        # The specific validation method will handle what to check
        return True
        
    def should_maintain_ligature_connection(self, distance: float) -> bool:
        """Determine if ligature connection should be maintained based on distance."""
        if self.ligature_binding == LigatureBindingMode.RIGID:
            return True
        elif self.ligature_binding == LigatureBindingMode.FLEXIBLE:
            # Allow some stretching but maintain connection
            return distance < 200  # Configurable threshold
        elif self.ligature_binding == LigatureBindingMode.DETACHABLE:
            # Allow detachment if moved too far
            return distance < 100
        else:  # FREE
            return False
            
    def get_validation_strictness(self) -> ValidationLevel:
        """Get the current validation strictness level."""
        return self.validation_level
        
    def can_perform_operation(self, operation: str, context: Dict[str, Any]) -> bool:
        """Check if an operation is allowed in the current mode."""
        config = self.mode_configs[self.current_mode]
        
        if operation == "move_outside_cut":
            return config['allow_containment_violation']
        elif operation == "violate_transformation_rule":
            return config['allow_rule_violation']
        elif operation == "create_invalid_structure":
            return self.validation_level in [ValidationLevel.NONE, ValidationLevel.BASIC]
        
        return True
        
    def get_mode_description(self) -> str:
        """Get a description of the current mode."""
        return self.mode_configs[self.current_mode]['description']
        
    def get_available_modes(self) -> List[InteractionMode]:
        """Get list of available interaction modes."""
        return list(InteractionMode)
        
    def get_mode_display_name(self, mode: InteractionMode) -> str:
        """Get a user-friendly display name for a mode."""
        display_names = {
            InteractionMode.CONSTRAINED: "Constrained Rearrangement",
            InteractionMode.COMPOSITION: "Free Composition", 
            InteractionMode.TRANSFORMATION: "Rule-based Transformation"
        }
        return display_names.get(mode, str(mode))

class ModeAwareValidator:
    """Validator that adapts behavior based on interaction mode."""
    
    def __init__(self, mode_manager: InteractionModeManager):
        self.mode_manager = mode_manager
        
    def validate_movement(self, node_id: str, new_position: QPointF, 
                         graph, cut_items: Dict) -> bool:
        """Validate movement based on current interaction mode."""
        
        if not self.mode_manager.should_validate_movement(node_id, new_position):
            return True  # Allow movement in flexible modes
            
        # Perform validation based on mode
        mode = self.mode_manager.get_mode()
        
        if mode == InteractionMode.CONSTRAINED:
            return self._validate_constrained_movement(node_id, new_position, graph, cut_items)
        elif mode == InteractionMode.TRANSFORMATION:
            return self._validate_transformation_movement(node_id, new_position, graph, cut_items)
        else:
            return True  # Composition mode allows free movement
            
    def _validate_constrained_movement(self, node_id: str, new_position: QPointF,
                                     graph, cut_items: Dict) -> bool:
        """Strict validation for constrained mode."""
        config = self.mode_manager.mode_configs[self.mode_manager.current_mode]
        
        # If containment violations are allowed, skip containment checking
        if config.get('allow_containment_violation', False):
            print(f"Containment violations allowed in {self.mode_manager.current_mode.name} mode")
            return True
        
        # Implement strict containment checking
        print(f"Checking containment for {node_id} at {new_position}")
        parent_node = graph.get_parent(node_id)
        if not parent_node:
            print(f"No parent found for {node_id}, allowing movement")
            return True
            
        print(f"Parent node: {parent_node.id}")
        if parent_node.id in cut_items:
            parent_cut = cut_items[parent_node.id]
            parent_rect = parent_cut.sceneBoundingRect()
            margin = 20
            valid_rect = parent_rect.adjusted(margin, margin, -margin, -margin)
            
            is_valid = valid_rect.contains(new_position)
            print(f"Parent rect: {parent_rect}, Valid rect: {valid_rect}")
            print(f"Position {new_position} is {'valid' if is_valid else 'invalid'}")
            return is_valid
        else:
            print(f"Parent {parent_node.id} not found in cut_items")
            
        return True
        
    def _validate_transformation_movement(self, node_id: str, new_position: QPointF,
                                        graph, cut_items: Dict) -> bool:
        """Rule-based validation for transformation mode."""
        # Implement Peirce's transformation rule validation
        # This would check if the movement violates any transformation rules
        return self._validate_constrained_movement(node_id, new_position, graph, cut_items)

class ModeAwareLigatureManager:
    """Ligature manager that adapts behavior based on interaction mode."""
    
    def __init__(self, mode_manager: InteractionModeManager):
        self.mode_manager = mode_manager
        
    def should_update_ligature(self, ligature_item, moved_item) -> bool:
        """Determine if ligature should update when connected item moves."""
        binding_mode = self.mode_manager.ligature_binding
        
        print(f"Checking if ligature should update, binding mode: {binding_mode}")
        
        if binding_mode == LigatureBindingMode.FREE:
            print("FREE binding mode - ligatures move independently")
            return False  # Ligatures move independently
        elif binding_mode == LigatureBindingMode.RIGID:
            print("RIGID binding mode - ligatures always update")
            return True  # Always maintain connection
        elif binding_mode == LigatureBindingMode.FLEXIBLE:
            print("FLEXIBLE binding mode - ligatures update with some tolerance")
            return True  # Update but allow some stretching
        elif binding_mode == LigatureBindingMode.DETACHABLE:
            print("DETACHABLE binding mode - ligatures update until distance threshold")
            # Calculate distance and check threshold
            return True  # For now, always update (could add distance checking)
            
        return True  # Default to updating
        
    def handle_ligature_stretch(self, ligature_item, distance: float):
        """Handle ligature stretching based on mode."""
        if not self.mode_manager.should_maintain_ligature_connection(distance):
            # Detach ligature
            self._detach_ligature(ligature_item)
        else:
            # Update path to maintain connection
            ligature_item.update_path()
            
    def _detach_ligature(self, ligature_item):
        """Detach a ligature from its endpoints."""
        # Implementation would remove connections and update visual state
        print(f"Detaching ligature {ligature_item.ligature_id}")
        
# Global mode manager instance
mode_manager = InteractionModeManager()


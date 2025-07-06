# Interaction Modes for Existential Graphs

## Overview

The enhanced existential graphs GUI now supports three distinct interaction modes, each designed for different use cases and constraint levels. This addresses the fundamental need to distinguish between different types of user interactions with logical expressions.

## The Three Interaction Modes

### 1. **Constrained Mode** (Ctrl+1)
**Purpose**: Rearrange existing well-formed logical expressions while preserving logical integrity.

**Characteristics**:
- **Strict Validation**: All movements are validated against containment rules
- **Rigid Ligature Binding**: Ligatures maintain connections when predicates move
- **No Rule Violations**: Cannot violate Peirce's transformation rules
- **Auto-Validation**: Real-time constraint checking

**Use Cases**:
- Reorganizing layout of existing proofs
- Cleaning up visual presentation of valid expressions
- Educational demonstrations of valid graph structures

**Behavior**:
- Predicates cannot be moved outside their containing cuts
- Ligatures automatically update to maintain connections
- Invalid operations are prevented with visual feedback

### 2. **Composition Mode** (Ctrl+2) - **Default**
**Purpose**: Free-form construction of new graphs with validation on demand.

**Characteristics**:
- **Basic Validation**: Minimal structural constraints
- **Flexible Ligature Binding**: Ligatures stretch but maintain connections
- **Rule Violations Allowed**: Freedom to create temporarily invalid structures
- **Manual Validation**: Validate when ready, not continuously

**Use Cases**:
- Constructing new logical expressions from scratch
- Experimental graph construction
- Learning and exploration without rigid constraints

**Behavior**:
- Predicates can be moved anywhere on the sheet
- Ligatures stretch to accommodate movement
- Validation available on demand (future feature)

### 3. **Transformation Mode** (Ctrl+3)
**Purpose**: Rule-based modifications following Peirce's transformation rules.

**Characteristics**:
- **Rule-Based Validation**: Enforces Peirce's specific transformation rules
- **Rigid Ligature Binding**: Maintains logical connections strictly
- **Transformation Rules**: Only allows operations permitted by EG rules
- **Context-Aware**: Distinguishes positive/negative contexts for rule application

**Use Cases**:
- Formal logical proofs and derivations
- Teaching Peirce's transformation rules
- Verifying logical equivalences

**Behavior**:
- Movements validated against transformation rules
- Context-sensitive operation permissions
- Automatic rule compliance checking

## Mode Switching

### GUI Controls
- **Toolbar Buttons**: Click mode buttons in the toolbar
- **Keyboard Shortcuts**:
  - `Ctrl+1`: Constrained Mode
  - `Ctrl+2`: Composition Mode  
  - `Ctrl+3`: Transformation Mode

### Visual Feedback
- **Mode Label**: Shows current mode in the information panel
- **Status Bar**: Displays mode description and current status
- **Console Output**: Detailed logging of mode changes and validations

## Technical Implementation

### Mode-Aware Components

#### **InteractionModeManager**
- Manages current mode and associated settings
- Provides configuration for validation levels and behaviors
- Emits signals when modes change

#### **ModeAwareValidator**
- Adapts validation behavior based on current mode
- Implements different constraint levels per mode
- Handles containment and rule-based validation

#### **ModeAwareLigatureManager**
- Controls ligature behavior based on mode
- Manages connection persistence and detachment
- Handles different binding strategies

### Validation Levels

1. **None**: No validation (not currently used)
2. **Basic**: Structural validation only
3. **Strict**: Full logical validation with containment
4. **Rule-Based**: Peirce's transformation rules enforcement

### Ligature Binding Modes

1. **Rigid**: Ligatures maintain connections rigidly
2. **Flexible**: Ligatures stretch but maintain connections  
3. **Detachable**: Ligatures can detach when moved too far
4. **Free**: Ligatures move independently (not currently used)

## Usage Examples

### Example 1: Reorganizing a Proof (Constrained Mode)
```
1. Switch to Constrained Mode (Ctrl+1)
2. Select and move predicates within their cuts
3. Ligatures automatically update to maintain connections
4. Invalid movements are prevented with visual feedback
```

### Example 2: Building a New Expression (Composition Mode)
```
1. Switch to Composition Mode (Ctrl+2) - Default
2. Add predicates and cuts freely
3. Create ligatures between predicates
4. Move elements anywhere on the sheet
5. Validate when construction is complete (future feature)
```

### Example 3: Applying Transformation Rules (Transformation Mode)
```
1. Switch to Transformation Mode (Ctrl+3)
2. Select elements to transform
3. Apply only operations allowed by Peirce's rules
4. System enforces context-sensitive constraints
5. Automatic validation of rule compliance
```

## Debug and Development

### Console Output
The system provides extensive debug output showing:
- Mode changes and configurations
- Validation decisions and reasoning
- Ligature update operations
- Constraint enforcement actions

### Customization
Mode behaviors can be customized by modifying the `mode_configs` dictionary in `InteractionModeManager`:

```python
self.mode_configs = {
    InteractionMode.CONSTRAINED: {
        'validation_level': ValidationLevel.STRICT,
        'ligature_binding': LigatureBindingMode.RIGID,
        'allow_containment_violation': False,
        # ... other settings
    }
}
```

## Future Enhancements

### Planned Features
1. **Manual Validation**: On-demand validation in Composition Mode
2. **Rule Suggestions**: Hints for valid transformations in Transformation Mode
3. **Undo/Redo**: Mode-aware operation history
4. **Custom Modes**: User-defined interaction modes
5. **Visual Indicators**: Enhanced feedback for mode-specific constraints

### Integration Points
- **Save/Load**: Mode information in saved graphs
- **Export**: Mode-specific export options
- **Collaboration**: Shared mode settings for team work

## Troubleshooting

### Common Issues

**Q: Predicates won't move in Constrained Mode**
A: Check that the target position is within the containing cut boundaries. The system prevents invalid movements.

**Q: Ligatures detach in Composition Mode**
A: This is expected behavior. Ligatures in Composition Mode can stretch and detach for maximum flexibility.

**Q: Can't perform certain operations in Transformation Mode**
A: Transformation Mode only allows operations permitted by Peirce's rules. Switch to Composition Mode for unrestricted editing.

### Debug Information
Enable detailed logging by checking console output. The system provides comprehensive information about:
- Why movements are rejected
- Which validation rules are being applied
- How ligatures are being updated
- Mode-specific behavior decisions

This interaction mode system provides the foundation for sophisticated, context-aware editing of existential graphs while maintaining the flexibility needed for different use cases.


# Copy/Paste Workflow for Existential Graphs

## Overview

The enhanced existential graphs GUI now supports sophisticated copy/paste operations that enable users to copy graphs constructed in **Composition Mode** and paste them into **Transformation Mode** for insertion into negative contexts, following Peirce's insertion rule.

## The Complete Workflow

### **Scenario: Composition → Transformation**

This addresses your specific question about copying a graph made in Composition Mode to Transformation Mode for insertion into a negative context.

```
1. Build graph freely in Composition Mode
2. Select and copy the graph fragment  
3. Switch to Transformation Mode
4. Paste into negative context (following insertion rule)
```

## Step-by-Step Instructions

### **Step 1: Create Graph in Composition Mode**

1. **Switch to Composition Mode** (Ctrl+2 or toolbar button)
2. **Build your graph freely**:
   - Add predicates and cuts without constraints
   - Create ligatures between predicates
   - Move elements anywhere on the sheet
   - Experiment with different structures

3. **Verify your construction**:
   - Check that predicates are properly connected
   - Ensure the graph represents your intended logic
   - Note: Validation is relaxed in this mode

### **Step 2: Copy the Graph Fragment**

1. **Select the elements** you want to copy:
   - Click and drag to select multiple items
   - Or Ctrl+click individual items
   - Include both predicates and any connecting ligatures

2. **Copy to clipboard**:
   - Press **Ctrl+C** or click **Copy** in toolbar
   - Status bar shows: "Copied N items from COMPOSITION mode"
   - Console shows detailed fragment information

### **Step 3: Switch to Transformation Mode**

1. **Change interaction mode**:
   - Press **Ctrl+3** or click **Transformation Mode** in toolbar
   - Mode label updates to show "Transformation Mode"
   - Status bar shows mode description

2. **Understand the new constraints**:
   - Only Peirce's transformation rules are allowed
   - Insertion rule: graphs can only be inserted in negative contexts
   - System will validate all operations

### **Step 4: Paste into Negative Context**

1. **Identify a negative context**:
   - Position cursor inside an odd number of cuts
   - Negative contexts appear inside cuts (odd nesting level)
   - System provides real-time validation feedback

2. **Attempt paste operation**:
   - Press **Ctrl+V** or click **Paste** in toolbar
   - System validates the insertion rule
   - Success: "Pasted at X, Y" 
   - Failure: "Cannot paste: Insertion rule violation"

## Context Analysis

### **Positive vs Negative Contexts**

The system automatically analyzes contexts based on cut nesting:

- **Positive Context** (Even number of cuts):
  - Root level (0 cuts)
  - Inside even-nested cuts (2, 4, 6...)
  - **Insertion NOT allowed** in Transformation Mode

- **Negative Context** (Odd number of cuts):
  - Inside odd-nested cuts (1, 3, 5...)
  - **Insertion allowed** in Transformation Mode

### **Visual Feedback**

- **Console output** shows context analysis
- **Status bar** explains why paste is rejected/allowed
- **Real-time validation** before paste operation

## Mode-Specific Behaviors

### **Composition Mode** (Source)
```
✓ Free construction and editing
✓ No validation constraints  
✓ Copy any selection
✓ Paste anywhere (if used as target)
```

### **Transformation Mode** (Target)
```
✓ Strict rule enforcement
✓ Context-sensitive validation
✓ Insertion rule compliance
✗ Paste rejected in positive contexts
```

### **Constrained Mode** (Alternative)
```
✓ Structural validation
✓ Containment rules enforced
✓ Paste with basic validation
```

## Technical Implementation

### **GraphClipboard System**

- **Fragment Serialization**: Preserves nodes, hyperedges, and metadata
- **Context Analysis**: Determines positive/negative contexts
- **Mode-Aware Validation**: Different rules per interaction mode
- **Rule Compliance**: Enforces Peirce's transformation rules

### **Key Components**

1. **GraphFragment**: Serializable representation of copied elements
2. **ContextAnalyzer**: Determines context types for insertion validation
3. **ModeAwareValidator**: Applies different validation rules per mode
4. **GraphClipboard**: Manages copy/paste operations with rule enforcement

## Example Workflows

### **Example 1: Building and Inserting a Conditional**

```
Composition Mode:
1. Create: Cat(x) → Animal(x)
2. Select both predicates and ligature
3. Copy (Ctrl+C)

Transformation Mode:
4. Switch mode (Ctrl+3)
5. Find negative context (inside a cut)
6. Paste (Ctrl+V) - Success!
```

### **Example 2: Rejected Insertion**

```
Transformation Mode:
1. Try to paste in positive context (root level)
2. System rejects: "Insertion rule violation"
3. Move to negative context (inside cut)
4. Paste succeeds with validation message
```

## Keyboard Shortcuts

- **Ctrl+C**: Copy selection
- **Ctrl+V**: Paste at cursor position
- **Ctrl+1**: Constrained Mode
- **Ctrl+2**: Composition Mode  
- **Ctrl+3**: Transformation Mode
- **Escape**: Clear selection

## Console Output Examples

### **Successful Copy**
```
Copying selection in COMPOSITION mode
Copied fragment with 2 nodes and 1 hyperedges
```

### **Successful Paste (Negative Context)**
```
Validating movement for paste in TRANSFORMATION mode
Context analysis: negative context (1 cuts)
Insertion allowed in negative context
Pasted fragment with 2 nodes
```

### **Rejected Paste (Positive Context)**
```
Validating movement for paste in TRANSFORMATION mode  
Context analysis: positive context (0 cuts)
Insertion rule violation: can only insert in negative contexts
```

## Advanced Features

### **Fragment Metadata**
- Source mode information
- Creation timestamp
- Node and hyperedge counts
- Bounding rectangle data

### **JSON Export**
- Export clipboard content to JSON
- Useful for debugging and analysis
- Preserves complete graph structure

### **Cross-Mode Compatibility**
- Fragments remember their source mode
- Validation adapts to target mode
- Seamless workflow between modes

## Troubleshooting

### **Common Issues**

**Q: Paste is rejected in Transformation Mode**
A: Check that you're pasting into a negative context (inside an odd number of cuts). The insertion rule only allows insertion in negative contexts.

**Q: Copy operation fails**
A: Ensure you have items selected that contain valid node_id attributes. Only graph elements (predicates, cuts) can be copied.

**Q: Ligatures don't copy correctly**
A: Ligatures are automatically included if they connect selected predicates. Ensure all connected predicates are selected.

### **Debug Information**

Enable detailed logging by monitoring console output:
- Copy operations show fragment details
- Paste operations show context analysis
- Validation explains rule compliance
- Mode changes show new constraints

## Future Enhancements

### **Planned Features**
- **Visual paste preview**: Show where fragment will be placed
- **Multi-clipboard**: Store multiple fragments
- **Paste with transformation**: Apply rules during paste
- **Import/Export**: Save fragments to files

### **Integration Opportunities**
- **Proof construction**: Copy lemmas between proofs
- **Template library**: Reusable graph patterns
- **Collaborative editing**: Share fragments between users

This copy/paste system provides the foundation for sophisticated graph construction workflows while maintaining strict compliance with Peirce's transformation rules when needed.


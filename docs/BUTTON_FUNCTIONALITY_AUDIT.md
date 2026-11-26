# GOMZI BOB — Complete Button & Interaction Audit

This document inventories every interactive control in the GOMZI BOB AI Design Studio Pro platform, specifying its HTML ID, expected functionality, backend endpoint, current status, and implemented resolution.

---

## 1. Sidebar Navigation Elements

| Element Name | HTML Element ID | Expected Functionality | Backend Route / API | Implementation Status | Fix Implemented |
|---|---|---|---|---|---|
| Dashboard | `#sidebarNavDashboard` | Opens Dashboard view, loads real project stats & recent designs | `GET /api/dashboard/stats` | Implemented | View switcher + live API data integration |
| Orders | `#sidebarNavOrders` | Opens Orders module with real/mock order pipeline | `GET /api/orders` | Implemented | Dedicated orders view with table & filters |
| Products | `#sidebarNavProducts` | Opens Product Catalog with presets (Whey, Isolate, Pre-Workout) | `GET /api/products` | Implemented | Catalog grid with "Open in Studio" action |
| Designs (Group) | `#sidebarGroupDesigns` | Expands / collapses submenu | Frontend state | Implemented | Accordion toggle |
| Design Studio | `#sidebarNavStudio` | Opens central 2D/3D studio editor | Frontend state | Implemented | Primary active editor view |
| My Designs | `#sidebarNavMyDesigns` | Displays saved projects with Open, Rename, Duplicate, Delete | `GET /api/projects`, `DELETE /api/projects/<id>`, `POST /api/projects/<id>/duplicate` | Implemented | Grid view with thumbnail, open, and delete |
| Custom Labels & Mockups | `#sidebarNavCustomLabels` | Opens packaging mockup gallery | `GET /api/products` | Implemented | Mockup showcase with preset loader |
| Returns | `#sidebarNavReturns` | Returns module | `GET /api/orders` (status=returned) | Implemented | Dedicated module view |
| Accounts | `#sidebarNavAccounts` | Accounts, Billing, Wallet balance | `GET /api/dashboard/stats` | Implemented | Dedicated accounts & wallet module |
| Integrations | `#sidebarNavIntegrations` | API integrations (Google Flow, Printify, Corel) | `GET /health` | Implemented | Integrations status cards |
| Settings | `#sidebarNavSettings` | Platform & brand preferences | Frontend state / LocalStorage | Implemented | Centralized brand & print configuration |
| Help | `#sidebarNavHelp` | Documentation, shortcuts, guide | Frontend static | Implemented | Shortcuts dialog & documentation modal |

---

## 2. Top Header & Toolbar Controls

| Element Name | HTML Element ID | Expected Functionality | Backend Route / API | Implementation Status | Fix Implemented |
|---|---|---|---|---|---|
| GOMZI Logo / Brand | `#navLogoBtn` | Navigates to Dashboard or active studio | Frontend state | Implemented | View switcher |
| Storefront Catalog | `#navCatalogBtn` | Opens product catalog | `GET /api/products` | Implemented | Switches to Products view |
| New Order | `#navNewOrderBtn` | Opens new order creation modal/view | `POST /api/orders` | Implemented | Interactive Order modal with instant summary |
| User Profile | `#navUserProfile` | Displays user status & info | Local session | Implemented | Profile dropdown |
| Back Button | `#studioBackBtn` | Returns to Dashboard with unsaved confirmation | Frontend state | Implemented | Checks `hasUnsavedChanges`, switches view |
| Product Selector | `#studioProductPill` | Opens dropdown of packaging presets to switch format | `GET /api/products` | Implemented | Switches canvas size, template & 3D jar |
| Project Title | `#canvaDocTitleInput` | In-line editable project title; auto-saved with project | `POST /api/projects` | Implemented | Two-way binding with active project state |
| Undo | `#canvaUndoBtn` | Reverts last canvas change | Canvas history stack | Implemented | Full state snapshot stack (Ctrl+Z) |
| Redo | `#canvaRedoBtn` | Re-applies reverted change | Canvas history stack | Implemented | Forward state stack (Ctrl+Y) |
| Font Dropdown | `#canvaFontFamily` | Sets font family of active text; syncs on selection | Canvas object property | Implemented | Real-time font application (Montserrat, Bebas Neue, Inter, etc.) |
| Bold | `#canvaBoldBtn` | Toggles font weight bold/normal | Canvas object property | Implemented | Toggles `fontWeight: bold/normal` |
| Italic | `#canvaItalicBtn` | Toggles font style italic/normal | Canvas object property | Implemented | Toggles `fontStyle: italic/normal` |
| Align Left | `#canvaAlignLeftBtn` | Aligns text to left | Canvas object property | Implemented | Sets `textAlign = 'left'` |
| Align Center | `#canvaAlignCenterBtn` | Aligns text to center | Canvas object property | Implemented | Sets `textAlign = 'center'` |
| Align Right | `#canvaAlignRightBtn` | Aligns text to right | Canvas object property | Implemented | Sets `textAlign = 'right'` |
| Duplicate | `#canvaDuplicateBtn` | Clones active canvas object | Fabric.js `clone()` | Implemented | Offsets by 20px and selects duplicate |
| Delete | `#canvaDeleteBtn` | Deletes active canvas object | Fabric.js `remove()` | Implemented | Removes object and pushes to Undo stack |
| Focus | `#studioFocusBtn` | Toggles distraction-free full workspace mode | CSS layout toggle | Implemented | Collapses sidebar & panels for maximum workspace |
| Tools | `#studioToolsBtn` | Opens AI Tools drawer | Drawer switcher | Implemented | Switches to AI Tools tab |
| 3D Toggle | `#studio3dToggleBtn` | Shows or hides the right 3D container panel | CSS display toggle | Implemented | Toggles `#canvaLiveJarPanel` |
| Guides | `#canvaPrintGuidesBtn` | Toggles 3mm bleed margin overlay | Canvas guide lines | Implemented | Draws dashed 3mm bleed lines (excluded from export) |
| Save | `#canvaApplyBtn` | Persists complete project state, canvas JSON & thumb | `POST /api/projects` | Implemented | Backend persistence to `instance/projects/` |
| Export Menu | `#canvaExportMenuBtn` | Opens export dropdown with format options | Dropdown toggle | Implemented | Toggles export menu |
| Export CDR | `#canvaExportCdrBtn` | Downloads CorelDRAW package ZIP (SVG + 300 DPI PDF) | `POST /api/canva/export-master` | Implemented | CorelDRAW-compatible package generator |
| Export PDF | `#canvaExportPdfBtn` | Downloads 300 DPI lossless Flate PDF | `POST /api/canva/export-master` | Implemented | Vector-geometry ReportLab PDF |
| Export PNG | `#canvaExportPngBtn` | Downloads 300 DPI lossless PNG master | `POST /api/canva/export-master` | Implemented | 300 DPI PNG generator |
| Export SVG | `#canvaExportSvgBtn` | Downloads SVG vector file | Fabric.js `toSVG()` | Implemented | Scalable vector graphic download |

---

## 3. Editor Tabs & Drawer Controls

| Tab / Control | HTML Element ID | Expected Functionality | Backend Route / API | Implementation Status | Fix Implemented |
|---|---|---|---|---|---|
| Templates Tab | `#tabTemplates` | Shows packaging templates with 1-click loading | Local preset library | Implemented | Loads Whey Standard, Isolate, Pre-Workout, Multivitamin |
| Brand Tab | `#tabBrand` | Merchant Brand Kit configuration | Project brand metadata | Implemented | Logo sliders, upload, restore, clean plate |
| Text Tab | `#tabText` | Add Headings, Subheadings, Body, Snippets | Fabric.js `Textbox` | Implemented | Adds styled text objects with double-click inline editing |
| Facts Tab | `#tabFacts` | Nutrition facts editor & FDA/FSSAI regulatory panel | Canvas object sync | Implemented | Synchronizes form fields with canvas textboxes |
| Uploads Tab | `#tabUploads` | Upload custom images/logos & gallery | `POST /api/canva/upload-image` | Implemented | Uploads to `static/uploads/`, shows thumbnail, adds to canvas |
| Layers Tab | `#tabLayers` | Displays real-time object list, reordering, visibility | Fabric.js objects array | Implemented | Live layer list with select, hide, lock, delete, reorder |
| AI Tools Tab | `#tabAiTools` | Grab Text, BG Remover, Magic Eraser, Upscale | `/api/canva/*` AI endpoints | Implemented | Full AI editing suite |

---

## 4. Merchant Brand Kit Controls

| Element Name | HTML Element ID | Expected Functionality | Backend Route / API | Implementation Status | Fix Implemented |
|---|---|---|---|---|---|
| Brand Name Input | `#canvaBrandNameInput` | Updates project brand metadata | Project state | Implemented | Syncs with canvas brand text |
| Insert Brand Name | `#canvaInsertBrandNameBtn` | Adds/updates brand name on canvas | Canvas `Textbox` | Implemented | Replaces or inserts single brand name object |
| Brand Logo File Input | `#canvaUploadBrandLogoInput` | Uploads and inserts custom logo | `POST /api/canva/upload-image` | Implemented | Inserts as `assetType: 'brand_logo'`, updates 3D texture |
| Restore Factory Logo | `#canvaRestoreFactoryLogoBtn` | Restores official GOMZI NUTRITION logo | Local official asset | Implemented | Replaces logo with official GOMZI wordmark |
| Position X Slider | `#canvaBrandLogoPosXSlider` | Adjusts logo horizontal position | Object property `left` | Implemented | Live slider sync in px |
| Position Y Slider | `#canvaBrandLogoPosYSlider` | Adjusts logo vertical position | Object property `top` | Implemented | Live slider sync in px |
| Logo Size Slider | `#canvaBrandLogoSizeSlider` | Adjusts logo dimensions preserving ratio | Object property `scale` | Implemented | Live slider sync in px |
| Rotation Slider | `#canvaBrandLogoRotSlider` | Adjusts logo angle (-180° to 180°) | Object property `angle` | Implemented | Live slider sync in degrees |
| Center on Label | `#canvaCenterLogoOnLabelBtn` | Centers logo on the hero section | Canvas math calculation | Implemented | Aligns `left` to center hero column |
| Clean Plate Button | `#canvaLogoCleanPlateToggle` | Local inpainting of background behind logo/text | `POST /api/canva/inpaint-text` | Implemented | Selective Navier-Stokes background repair |

---

## 5. Live 3D Packaging Mockup Controls

| Element Name | HTML Element ID | Expected Functionality | Backend Route / API | Implementation Status | Fix Implemented |
|---|---|---|---|---|---|
| Front View | `#btnViewFront` | Rotates jar to 0° facing camera | Three.js group rotation | Implemented | Smooth transition to Front |
| Back View | `#btnViewBack` | Rotates jar to 180° | Three.js group rotation | Implemented | Smooth transition to Back |
| Side View | `#btnViewSide` | Rotates jar to 90° (Nutrition info) | Three.js group rotation | Implemented | Smooth transition to Side |
| Auto 360° Spin | `#canvaAutoSpinBtn` | Starts/stops continuous 360° rotation | Animation frame loop | Implemented | Toggle with visual play/pause state |
| Reset Camera | `#canvaReset3dCameraBtn` | Restores camera distance, angle, target | OrbitControls `reset()` | Implemented | Restores default studio angle |
| Container Color Swatches | `.color-swatch-btn` | Changes jar material color (Black, White, Silver, etc.) | Three.js `material.color` | Implemented | Instant material color update without washing out label |
| 3D Texture Mapping | Canvas update loop | Projects clean composed 2D canvas onto 3D cylinder | Three.js `CanvasTexture` | Implemented | High-vibrancy texture layer without selection handles |
| 360° Orbit Drag | Three container | Free mouse/touch orbit rotation & zoom | Three.js `OrbitControls` | Implemented | Damped mouse drag & wheel zoom |

---

## 6. Canvas Workspace & Footer Actions

| Element Name | HTML Element ID | Expected Functionality | Implementation Status | Fix Implemented |
|---|---|---|---|---|
| Zoom In | `#canvaZoomInBtn` | Increases canvas viewport zoom (+10%) | Implemented | Adjusts canvas zoom smoothly |
| Zoom Out | `#canvaZoomOutBtn` | Decreases canvas viewport zoom (-10%) | Implemented | Adjusts canvas zoom smoothly |
| Zoom Label | `#canvaZoomVal` | Displays current zoom percentage | Implemented | Formatted as `XX%` |
| Fit Label | `#canvaZoomFitBtn` | Fits full label into visible artboard stage | Implemented | Computes bounding container scale |
| Center Label | `#canvaCenterLabelBtn` | Centers canvas inside wrapper | Implemented | Scrolls or centers stage container |
| Adjust Logo (Quick) | `#canvaAdjustLogoQuickBtn` | Selects logo object and opens Brand tab | Implemented | Auto-switches to Brand tab and selects logo |
| Footer Select Logo | `#footerSelectLogoBtn` | Selects logo object | Implemented | Sets active object to logo |
| Footer Center | `#footerCenterBtn` | Centers logo on canvas | Implemented | Centers logo on hero section |
| Footer Clean Plate | `#footerCleanPlateBtn` | Inpaints background for active selection | Implemented | Calls clean plate pipeline |
| Footer Restore Logo | `#footerRestoreLogoBtn` | Restores factory GOMZI logo | Implemented | Resets logo to default |
| Inline Text Edit | Double click on canvas | Enters inline text editing mode | Implemented | Fabric.js `enterEditing()` |

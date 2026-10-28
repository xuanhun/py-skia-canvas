"""Regression guards for mechanical extraction, not GPU or Python acceptance."""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.validate_core import validate


class CoreExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        document = json.loads((ROOT / "crates/source-map.json").read_text(encoding="utf-8"))
        files = {"crates/source-map.json"}
        files.update(entry["path"] for entry in document.get("newFiles", []))
        for entry in document["files"]:
            files.update([entry["source"], entry["destination"]])
        for relative in files:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)

    def test_current_mechanical_extraction(self):
        self.assertEqual([], validate(self.root)["errors"])

    def test_owner_exit_cannot_leak_the_original_gpu_context(self):
        path=self.root/'crates/canvas-core/src/gpu/vulkan/engine.rs'
        text=path.read_text(encoding='utf-8')
        self.assertIn('drop(context.take())',text)
        path.write_text(text.replace('drop(context.take())','std::mem::forget(context.take())',1),encoding='utf-8')
        self.assertTrue(validate(self.root)['errors'])

    def test_observation_cannot_change_original_layout(self):
        path=self.root/'crates/canvas-core/src/typography.rs';source=path.read_text(encoding='utf-8')
        path.write_text(source.replace('paragraph.layout(self.width)','paragraph.layout(1.0)',1),encoding='utf-8')
        self.assertIn('Original layout changed beyond same-Paragraph observation',validate(self.root)['errors'])

    def test_original_v8_decimal_format_cannot_change(self):
        path=self.root/'crates/python/vendor/v8-numbers/format.cpp';source=path.read_text(encoding='utf-8')
        path.write_text(source.replace('decimal_point <= 21','decimal_point <= 22',1),encoding='utf-8')
        self.assertIn('Original V8 decimal format block changed',validate(self.root)['errors'])

    def test_original_canvas_gamma_condition_is_retained(self):
        path=self.root/'crates/canvas-core/src/canvas/construction.rs'
        source=path.read_text(encoding='utf-8');self.assertIn('text_contrast > max_g',source)
        path.write_text(source.replace('text_contrast > max_g','text_gamma > max_g',1),encoding='utf-8')
        self.assertIn('Original Canvas construction validation changed',validate(self.root)['errors'])

    def test_original_argument_stage_is_retained(self):
        path=self.root/'python/py_skia_canvas/_argument_specs.py'
        source=path.read_text(encoding='utf-8');self.assertIn("'cp1x'",source)
        path.write_text(source.replace("'cp1x'","'controlX'",1),encoding='utf-8')
        self.assertIn('Original float argument declarations changed',validate(self.root)['errors'])

    def test_original_window_fit_cannot_be_rewritten(self):
        path=self.root/'crates/canvas-core/src/gui/window.rs';source=path.read_text(encoding='utf-8');self.assertIn('Fit::ContainX => fit_x',source)
        path.write_text(source.replace('Fit::ContainX => fit_x','Fit::ContainX => fit_y'),encoding='utf-8')
        self.assertIn('Original GUI native body changed: window.rs',validate(self.root)['errors'])

    def test_original_gui_cadence_cannot_be_rewritten(self):
        path=self.root/'crates/canvas-core/src/gui/app.rs';source=path.read_text(encoding='utf-8');self.assertIn('1_500_000',source)
        path.write_text(source.replace('1_500_000','1_000_000'),encoding='utf-8')
        self.assertIn('Original GUI loop/cadence changed beyond language scheduling separation',validate(self.root)['errors'])

    def test_original_v8_math_cannot_change(self):
        path=self.root/'crates/python/vendor/v8/src/base/ieee754.cc'
        source=path.read_text(encoding='utf-8')
        coefficient='6.36619772367581382433e-01'
        self.assertIn(coefficient,source)
        path.write_text(source.replace(coefficient,'6.36619772367581382434e-01',1),encoding='utf-8')
        self.assertIn('Working V8 math source changed: ieee754.cc',validate(self.root)['errors'])

    def test_v8_math_contraction_flag_cannot_disappear(self):
        path=self.root/'crates/python/build.rs'
        source=path.read_text(encoding='utf-8')
        path.write_text(source.replace('-ffp-contract=off','-unused-flag'),encoding='utf-8')
        self.assertIn('V8 math FP flags missing',validate(self.root)['errors'])

    def test_projection_basis_cannot_change(self):
        path=self.root/'crates/canvas-core/src/context/operations.rs'
        source=path.read_text(encoding='utf-8')
        text='0 => this.bounds.to_quad().to_vec()'
        self.assertIn(text,source)
        path.write_text(source.replace(text,'0 => Rect::from_wh(1.0,1.0).to_quad().to_vec()',1),encoding='utf-8')
        self.assertIn('Original context operation fragments changed',validate(self.root)['errors'])

    def test_number_string_unsigned_prefix_cannot_change(self):
        path=self.root/'crates/canvas-core/src/utils.rs'
        source=path.read_text(encoding='utf-8')
        text='u64::from_str_radix(s, 16)'
        self.assertIn(text,source)
        path.write_text(source.replace(text,'i64::from_str_radix(s, 16)',1),encoding='utf-8')
        self.assertIn('Original numeric string parsing changed',validate(self.root)['errors'])

    def test_filter_coefficient_change_is_rejected(self):
        path = self.root / "crates/canvas-core/src/filter.rs"
        source = path.read_text(encoding="utf-8")
        self.assertIn("127.0 + amt * orig", source)
        path.write_text(source.replace("127.0 + amt * orig", "128.0 + amt * orig"), encoding="utf-8")
        self.assertIn("Filter extraction changed more than documentation", validate(self.root)["errors"])

    def test_node_path_adapter_cannot_change_unmapped_code(self):
        path = self.root / "crates/node/src/path.rs"
        path.write_bytes(path.read_bytes() + b"\n// unexpected edit\n")
        self.assertIn("Node Path2D changed beyond declared core forwarding and boxing", validate(self.root)["errors"])

    def test_current_path_transform_fragment_cannot_change(self):
        path = self.root / "crates/canvas-core/src/context/operations.rs"
        source = path.read_text(encoding="utf-8")
        path.write_text(source.replace("ctm.pre_translate((*dx, *dy))", "ctm.pre_translate((*dy, *dx))"), encoding="utf-8")
        self.assertIn("Original context operation fragments changed", validate(self.root)["errors"])

    def test_original_ellipse_rounding_cannot_change(self):
        path = self.root / "crates/canvas-core/src/path.rs"
        source = path.read_text(encoding="utf-8")
        path.write_text(source.replace("10000.0", "1000.0"), encoding="utf-8")
        self.assertIn("Original Path2D primitives changed", validate(self.root)["errors"])

    def test_path_interpolation_order_cannot_change(self):
        path = self.root / "crates/canvas-core/src/path/operations.rs"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("other.path.interpolate(&this.path, weight)", "this.path.interpolate(&other.path, weight)"), encoding="utf-8")
        self.assertIn("Original Path2D operation fragments changed", validate(self.root)["errors"])

    def test_path_effect_fallback_cannot_change(self):
        path = self.root / "crates/canvas-core/src/path/operations.rs"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("Path2D{path:this.path.clone()}", "Path2D{path:Path::new()}"), encoding="utf-8")
        self.assertIn("Original Path2D operation fragments changed", validate(self.root)["errors"])

    def test_node_cannot_reintroduce_a_filter_implementation(self):
        path = self.root / "crates/node/src/filter.rs"
        path.write_bytes(path.read_bytes() + b"\nimpl Filter {}\n")
        self.assertIn("Node must use the shared filter implementation", validate(self.root)["errors"])

    def test_core_cannot_import_neon(self):
        path = self.root / "crates/canvas-core/src/utils.rs"
        path.write_bytes(path.read_bytes() + b"\nuse neon::prelude::*;\n")
        self.assertTrue(any("Language/thread boundary violation" in error for error in validate(self.root)["errors"]))

    def test_gradient_stop_order_cannot_change(self):
        path = self.root / "crates/canvas-core/src/gradient.rs"
        source = path.read_text(encoding="utf-8")
        self.assertIn("n-f32::EPSILON", source)
        path.write_text(source.replace("n-f32::EPSILON", "n+f32::EPSILON"), encoding="utf-8")
        self.assertTrue(any("Original method body changed: add_stop" in error for error in validate(self.root)["errors"]))

    def test_gradient_offset_boundary_cannot_change(self):
        path = self.root / "crates/canvas-core/src/gradient.rs"
        source = path.read_text(encoding="utf-8")
        path.write_text(source.replace("offset > 1.0", "offset >= 1.0"), encoding="utf-8")
        self.assertIn("Original gradient offset validation changed", validate(self.root)["errors"])

    def test_broken_content_clone_behavior_cannot_be_silently_fixed(self):
        path = self.root / "crates/canvas-core/src/image.rs"
        source = path.read_text(encoding="utf-8")
        self.assertIn("_ => Content::default()", source)
        path.write_text(source.replace("_ => Content::default()", "_ => Content::Broken"), encoding="utf-8")
        self.assertTrue(any("Original method body changed: clone" in error for error in validate(self.root)["errors"]))

    def test_gpu_device_order_cannot_change(self):
        path = self.root / "crates/canvas-core/src/gpu/vulkan/engine.rs"
        source = path.read_text(encoding="utf-8")
        self.assertIn("PhysicalDeviceType::DiscreteGpu => 0", source)
        path.write_text(source.replace("PhysicalDeviceType::DiscreteGpu => 0", "PhysicalDeviceType::DiscreteGpu => 2"), encoding="utf-8")
        self.assertTrue(any("Original method body changed: new" in error for error in validate(self.root)["errors"]))

    def test_surface_origin_cannot_change(self):
        path = self.root / "crates/canvas-core/src/gpu/vulkan/engine.rs"
        source = path.read_text(encoding="utf-8")
        self.assertIn("SurfaceOrigin::BottomLeft", source)
        path.write_text(source.replace("SurfaceOrigin::BottomLeft", "SurfaceOrigin::TopLeft"), encoding="utf-8")
        self.assertTrue(any("Original method body changed: surface" in error for error in validate(self.root)["errors"]))

    def test_utf16_metrics_indices_cannot_change(self):
        path = self.root / "crates/canvas-core/src/typography.rs"
        source = path.read_text(encoding="utf-8")
        self.assertIn("c.len_utf16()", source)
        path.write_text(source.replace("c.len_utf16()", "c.len_utf8()"), encoding="utf-8")
        self.assertTrue(any("Original method body changed: utf16_range" in error for error in validate(self.root)["errors"]))

    def test_original_windows_font_decode_fallback_is_retained(self):
        path=self.root/'crates/canvas-core/src/font_library.rs'
        source=path.read_text(encoding='utf-8')
        self.assertIn('}.unwrap_or(bytes);',source)
        path.write_text(source.replace('}.unwrap_or(bytes);','}.unwrap_or_default();',1),encoding='utf-8')
        self.assertIn('Original font load_typeface fragment changed',validate(self.root)['errors'])

    def test_original_font_metadata_alias_is_retained(self):
        path=self.root/'crates/canvas-core/src/font_library.rs'
        source=path.read_text(encoding='utf-8')
        self.assertIn('Some(name) => name,',source)
        path.write_text(source.replace('Some(name) => name,','Some(_name) => font.family_name(),',1),encoding='utf-8')
        self.assertIn('Original font typeface_metadata fragment changed',validate(self.root)['errors'])

    def test_original_font_line_height_ratio_is_retained(self):
        path=self.root/'crates/canvas-core/src/typography.rs'
        source=path.read_text(encoding='utf-8')
        self.assertIn('.map(|pt_size| pt_size / size)',source)
        path.write_text(source.replace('.map(|pt_size| pt_size / size)','.map(|pt_size| pt_size)',1),encoding='utf-8')
        self.assertIn('Original typed FontSpec packing changed',validate(self.root)['errors'])

    def test_original_empty_font_family_rule_is_retained(self):
        path=self.root/'crates/canvas-core/src/typography.rs'
        source=path.read_text(encoding='utf-8')
        self.assertIn('match families[0] == ""{',source)
        path.write_text(source.replace('match families[0] == ""{','match families[0] == "serif"{',1),encoding='utf-8')
        self.assertIn('Original typed FontSpec packing changed',validate(self.root)['errors'])

    def test_original_spacing_uses_current_em_size(self):
        path=self.root/'crates/canvas-core/src/context/text_state.rs'
        source=path.read_text(encoding='utf-8');self.assertIn('spacing.in_px(em_size)',source)
        path.write_text(source.replace('spacing.in_px(em_size)','spacing.in_px(16.0)',1),encoding='utf-8')
        self.assertIn('Original text-state operation fragments changed',validate(self.root)['errors'])

    def test_original_text_feature_map_is_complete(self):
        path=self.root/'python/py_skia_canvas/_text_css_data.py'
        source=path.read_text(encoding='utf-8');self.assertIn("'common-ligatures': ['liga', 'clig']",source)
        path.write_text(source.replace("'common-ligatures': ['liga', 'clig']","'common-ligatures': ['liga']",1),encoding='utf-8')
        self.assertIn('Original CSS font feature tables changed',validate(self.root)['errors'])

    def test_original_decoration_current_color_guard_is_retained(self):
        path=self.root/'crates/canvas-core/src/typography/decoration.rs'
        source=path.read_text(encoding='utf-8');self.assertIn('css.is_empty() || color.is_none()',source)
        path.write_text(source.replace('css.is_empty() || color.is_none()','css.is_empty()',1),encoding='utf-8')
        self.assertIn('Original decoration argument fragment changed',validate(self.root)['errors'])

    def test_original_decoration_through_mode_is_retained(self):
        path=self.root/'crates/canvas-core/src/typography/decoration.rs'
        source=path.read_text(encoding='utf-8');self.assertIn('let mode = TextDecorationMode::Through;',source)
        path.write_text(source.replace('let mode = TextDecorationMode::Through;','let mode = TextDecorationMode::Gaps;',1),encoding='utf-8')
        self.assertIn('Original decoration argument fragment changed',validate(self.root)['errors'])

    def test_original_svg_default_size_is_retained(self):
        path=self.root/'crates/canvas-core/src/image/loading.rs'
        source=path.read_text(encoding='utf-8');self.assertIn('150.0 * aspect, 150.0',source)
        path.write_text(source.replace('150.0 * aspect, 150.0','300.0 * aspect, 300.0',1),encoding='utf-8')
        self.assertIn('Original image extraction changed: loading.rs',validate(self.root)['errors'])

    def test_original_draw_image_ignored_snap_result_is_retained(self):
        path=self.root/'crates/canvas-core/src/image/operations.rs'
        source=path.read_text(encoding='utf-8');self.assertIn('    content.snap_rects_to_bounds(src, dst);',source)
        path.write_text(source.replace('    content.snap_rects_to_bounds(src, dst);','    let (src, dst) = content.snap_rects_to_bounds(src, dst);',1),encoding='utf-8')
        self.assertIn('Original image extraction changed: operations.rs',validate(self.root)['errors'])

    def test_original_dirty_negative_origin_is_retained(self):
        path=self.root/'crates/canvas-core/src/image/operations.rs'
        source=path.read_text(encoding='utf-8');self.assertIn('*dx -= *dw;',source)
        path.write_text(source.replace('*dx -= *dw;','*dx += *dw;',1),encoding='utf-8')
        self.assertIn('Original image extraction changed: operations.rs',validate(self.root)['errors'])

    def test_effect_blend_updates_original_paint_and_state(self):
        path=self.root/'crates/canvas-core/src/context/effects.rs'
        source=path.read_text(encoding='utf-8');self.assertIn('this.state.paint.set_blend_mode(mode);',source)
        path.write_text(source.replace('    this.state.paint.set_blend_mode(mode);\n','',1),encoding='utf-8')
        self.assertIn('Original effect state fragments changed',validate(self.root)['errors'])

    def test_filter_spec_preserves_original_insertion_order(self):
        path=self.root/'crates/canvas-core/src/filter/arguments.rs'
        source=path.read_text(encoding='utf-8');self.assertIn('for name in names',source)
        path.write_text(source.replace('for name in names','for name in names.into_iter().rev()',1),encoding='utf-8')
        self.assertIn('Original FilterSpec packing changed',validate(self.root)['errors'])

    def test_drop_shadow_original_blur_field_is_retained(self):
        path=self.root/'crates/canvas-core/src/filter/arguments.rs'
        source=path.read_text(encoding='utf-8');self.assertIn('blur: dims[2]',source)
        path.write_text(source.replace('blur: dims[2]','blur: dims[0]',1),encoding='utf-8')
        self.assertIn('Original FilterSpec packing changed',validate(self.root)['errors'])

    def test_original_variable_weight_rule_is_retained(self):
        path = self.root / "crates/canvas-core/src/font_library.rs"
        source = path.read_text(encoding="utf-8")
        self.assertIn("style.font_style().weight() - 1", source)
        path.write_text(source.replace("style.font_style().weight() - 1", "style.font_style().weight()"), encoding="utf-8")
        self.assertTrue(any("Original method body changed: fonts_for_style" in error for error in validate(self.root)["errors"]))


if __name__ == "__main__":
    unittest.main()

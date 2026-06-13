import json
import uuid

# Google Slides GWT "punch" format uses centipoints (1/100 pt) for coordinates.
# Empirically, 1 CSS pixel maps to 508 centipoints for translations.
CP = 508.0

# Default internal bounding-box sizes (centipoints) used by Slides for scaling.
RECT_DENOM = 120000.0   # rectangles and ellipses
LINE_DENOM = 120000.0   # line/connector shapes (type 153)
TEXT_DENOM = 100000.0   # text boxes (type 108)

class SlidesBuilder:
    """
    High-level builder for Google Slides GWT "punch" clipboard payloads.

    Usage:
        b = SlidesBuilder(font_family='Ubuntu')
        b.add_rect(...)
        b.add_line(...)
        b.add_text(...)
        b.add_image(...)
        b.add_group([...])
        payload = b.to_punch()
    """

    def __init__(self, font_family='Ubuntu'):
        self.font_family = font_family
        self.resolved = []
        self.unresolved = []
        self.autotext_content = {}
        self.image_blobs = []
        self._id_counter = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _next_id(self, hint='el'):
        self._id_counter += 1
        return f"{hint}_{self._id_counter}"

    def _register_autotext(self, obj_id):
        key = json.dumps({"shapeId": obj_id}, separators=(',', ':'))
        self.autotext_content[key] = {}

    def _add_op(self, op):
        self.resolved.append(op)
        self.unresolved.append(op)
        return op

    def _fmt_op(self, obj_id, length=1, align=2):
        # Default center alignment paragraph format op.
        return [17, obj_id, None, 0, length, [], [12, align]]

    @staticmethod
    def _cp(value):
        return int(round(float(value or 0) * CP))

    @staticmethod
    def _scale(dim_px, denom):
        v = (float(dim_px or 0) * CP) / denom
        # Avoid exactly-zero scales; 0.0004 matches native reference.
        if v == 0:
            return 0.0004
        return v

    @staticmethod
    def _color(c):
        return str(c).upper() if c else 'NONE'

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------
    def add_rect(self, x, y, width, height, fill='none', stroke='#000000',
                 stroke_width=2.0, obj_id=None):
        obj_id = obj_id or self._next_id('rect')
        x_cp = self._cp(x)
        y_cp = self._cp(y)
        scale_x = self._scale(width, RECT_DENOM)
        scale_y = self._scale(height, RECT_DENOM)

        fill = fill or 'none'
        stroke = stroke or 'none'
        stroke_width = float(stroke_width if stroke_width is not None else 2.0)

        is_filled = 1 if fill != 'none' else 0
        # Native copies always supply a real hex for key 15 even when fill is off.
        fill_color = self._color(fill) if fill != 'none' else '#EEEEEE'
        stroke_color = self._color(stroke)

        style = [
            14, is_filled,
            15, fill_color,
            18, 1,
            19, stroke_color,
            22, int(round(stroke_width * CP)),
            43, 0,
            60, 0,
        ]

        op = [3, obj_id, 6, [scale_x, 0, 0, scale_y, x_cp, y_cp], style, "p"]
        self._add_op(op)
        self._add_op(self._fmt_op(obj_id))
        self._register_autotext(obj_id)
        return obj_id

    def add_ellipse(self, x, y, width, height, fill='none', stroke='#000000',
                    stroke_width=2.0, obj_id=None):
        obj_id = obj_id or self._next_id('ellipse')
        x_cp = self._cp(x)
        y_cp = self._cp(y)
        scale_x = self._scale(width, RECT_DENOM)
        scale_y = self._scale(height, RECT_DENOM)

        fill = fill or 'none'
        stroke = stroke or 'none'
        stroke_width = float(stroke_width if stroke_width is not None else 2.0)

        is_filled = 1 if fill != 'none' else 0
        fill_color = self._color(fill) if fill != 'none' else 'none'
        stroke_color = self._color(stroke)

        style = [14, is_filled]
        if fill != 'none':
            style.extend([15, fill_color])
        else:
            style.extend([15, 'none'])
        if stroke != 'none':
            style.extend([19, stroke_color, 22, int(round(stroke_width * CP))])
        else:
            style.extend([19, 'none'])

        op = [3, obj_id, 8, [scale_x, 0, 0, scale_y, x_cp, y_cp], style, "p"]
        self._add_op(op)
        return obj_id

    def add_line(self, x1, y1, x2, y2, stroke='#000000', stroke_width=2.0,
                 dasharray=None, arrow_start=False, arrow_end=False, obj_id=None):
        obj_id = obj_id or self._next_id('line')
        x1 = float(x1 or 0)
        y1 = float(y1 or 0)
        x2 = float(x2 or 0)
        y2 = float(y2 or 0)
        dx = x2 - x1
        dy = y2 - y1

        scale_x = (dx * CP) / LINE_DENOM
        scale_y = (dy * CP) / LINE_DENOM
        if scale_x == 0:
            scale_x = 0.0004
        if scale_y == 0:
            scale_y = 0.0004

        x_cp = self._cp(x1)
        y_cp = self._cp(y1)

        stroke = stroke or 'none'
        stroke_width = float(stroke_width if stroke_width is not None else 2.0)
        has_dash = dasharray and str(dasharray) != 'none'

        style = [
            14, 0,
            15, '#EEEEEE',
            18, 1,
            19, self._color(stroke),
            22, int(round(stroke_width * CP)),
            27, 1.3,
            30, 1.3,
            43, 2 if has_dash else 0,
        ]
        if arrow_start:
            style.extend([28, 5])
        if arrow_end:
            style.extend([29, 5])

        op = [3, obj_id, 153, [scale_x, 0, 0, scale_y, x_cp, y_cp], style, "p"]
        self._add_op(op)
        return obj_id

    def add_text(self, x, y, text, width=None, height=None, font_size=16,
                 color='#000000', align='start', bold=False, italic=False,
                 font_family=None, obj_id=None):
        obj_id = obj_id or self._next_id('text')
        text_str = str(text or '')
        align = align or 'start'
        color = color or '#000000'
        font_family = font_family or self.font_family

        # Default sizing mimics the original app.py behaviour.
        box_w = float(width if width is not None else 400)
        box_h = float(height if height is not None else (font_size * 2.5))

        tx = float(x or 0)
        if align in ('center', 'middle'):
            tx -= box_w / 2.0
        elif align in ('right', 'end'):
            tx -= box_w
        ty = float(y or 0) - (box_h / 2.0)

        real_w = float(width if width is not None else 333.33)
        real_h = float(height if height is not None else 37.5)

        x_cp = self._cp(tx)
        y_cp = self._cp(ty)
        scale_x = self._scale(real_w, TEXT_DENOM)
        scale_y = self._scale(real_h, TEXT_DENOM)

        op = [3, obj_id, 108, [scale_x, 0, 0, scale_y, x_cp, y_cp], [44, 0], "p"]
        self._add_op(op)

        if text_str:
            n_chars = len(text_str)
            self._add_op([15, obj_id, None, 0, text_str])

            align_val = 1
            if align in ('center', 'middle'):
                align_val = 2
            elif align in ('right', 'end'):
                align_val = 3
            self._add_op([17, obj_id, None, n_chars, n_chars + 1, [], [12, align_val]])

            typography = []
            if bold:
                typography.extend([0, 1])
            if italic:
                typography.extend([1, 1])
            if color and color != 'none':
                typography.extend([4, self._color(color)])
            typography.extend([5, font_family or 'Ubuntu'])
            typography.extend([6, int(round(float(font_size or 16)))])
            self._add_op([17, obj_id, None, 0, n_chars + 1, [], typography])

            self._register_autotext(obj_id)

        return obj_id

    def add_image(self, x, y, width_pt, height_pt, image_url,
                  native_width_px, native_height_px, obj_id=None):
        """
        Add a SHAPE_TYPE_3 image placeholder used by Google Slides for
        pasted images (including rendered LaTeX equations).

        width_pt and height_pt are the desired size on the slide in points.
        native_width_px and native_height_px are the intrinsic pixel
        dimensions of the image file (used for transform scaling).
        """
        obj_id = obj_id or self._next_id('image')
        x_cp = self._cp(x)
        y_cp = self._cp(y)

        width_pt = float(width_pt or 100)
        height_pt = float(height_pt or 100)
        native_w = max(int(native_width_px or 1), 1)
        native_h = max(int(native_height_px or 1), 1)

        # Image placeholders scale by (size_in_cp / native_px).
        scale_x = (width_pt * CP) / native_w
        scale_y = (height_pt * CP) / native_h

        blob_id = f"s-blob-v1-IMAGE-{uuid.uuid4().hex[:12]}"

        style = [
            15, '#EEEEEE',
            177, 0,
            19, '#595959',
            22, 381,
            39, str(image_url),
            49, blob_id,
            8, native_w,
            9, native_h,
        ]

        op = [3, obj_id, 3, [scale_x, 0, 0, scale_y, x_cp, y_cp], style, "p"]
        self._add_op(op)
        # Image placeholders in native equation copies are NOT registered in
        # autotext_content; keep that map empty for images.

        self.image_blobs.append({
            'blob_id': blob_id,
            'image_url': str(image_url),
            'width_pt': width_pt,
            'height_pt': height_pt,
            'native_w': native_w,
            'native_h': native_h,
        })
        return obj_id

    def add_group(self, children, obj_id=None):
        obj_id = obj_id or self._next_id('group')
        op = [2, obj_id, list(children), [1, 0, 0, 1, 0, 0], "p"]
        self._add_op(op)
        return obj_id

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    def to_punch(self, dih=1245482604,
                 edi="kBeECgZrwyN4Pk3CGalAkiIcibCHBxM0-dGHUMnfHDgyvkMYVZ_pxB9fogazgDhzNcbMktVjXdXLwpNCRHaU0vvKDDCQIvYzhuttxtQqAThS",
                 edrk="We7cOKI5bHNbFvbICo1cgW8xvwoMCQ_DEW3hRvkC3-q7k9z-tw..",
                 dct="punch", ds=False, cses=False, sm="other"):
        flat_payload = {
            "resolved": self.resolved,
            "unresolved": self.unresolved,
            "autotext_content": self.autotext_content,
            "did_remove_empty_picture_placeholders": False,
            "copy_source_supports_inheritance_via_master": True,
        }
        flat_str = json.dumps(flat_payload, separators=(',', ':'))

        wrapped_payload = {
            "dih": dih,
            "data": flat_str,
            "edi": edi,
            "edrk": edrk,
            "dct": dct,
            "ds": ds,
            "cses": cses,
            "sm": sm,
        }
        wrapped_str = json.dumps(wrapped_payload, separators=(',', ':'))

        result = {"flat": flat_str, "wrapped": wrapped_str}

        # If images were added, produce the auxiliary Google Docs clipboard
        # MIME types required for image paste (document-slice-clip and
        # image-clip).  These are optional for some pastes but match the
        # native Google Slides copy format more closely.
        if self.image_blobs:
            document_slice = self._build_document_slice()
            image_clip = self._build_image_clip()

            doc_slice_wrapped = {
                "dih": dih,
                "data": json.dumps(document_slice, separators=(',', ':')),
                "edi": edi,
                "edrk": edrk,
                "dct": dct,
                "ds": ds,
                "cses": cses,
                "sm": sm,
            }
            image_clip_wrapped = {
                "dih": dih,
                "data": json.dumps(image_clip, separators=(',', ':')),
                "edi": edi,
                "edrk": edrk,
                "dct": dct,
                "ds": ds,
                "cses": cses,
                "sm": sm,
            }
            result["document_slice_wrapped"] = json.dumps(doc_slice_wrapped, separators=(',', ':'))
            result["image_clip_wrapped"] = json.dumps(image_clip_wrapped, separators=(',', ':'))

        return result

    def _build_document_slice(self):
        entity_map = {}
        entity_position_map = []
        entity_type_map = {}

        for blob in self.image_blobs:
            kix_id = f"kix.{uuid.uuid4().hex[:12]}"
            entity_position_map.append([kix_id])
            entity_type_map[kix_id] = "inline"
            entity_map[kix_id] = {
                "ee_eo": {
                    "eo_type": 0,
                    "i_wth": float(blob['width_pt']),
                    "i_ht": float(blob['height_pt']),
                    "eo_lco": {
                        "lc_ct": 0,
                        "lc_sci": "",
                        "lc_srk": "",
                        "lc_oi": "",
                        "lc_cs": ""
                    },
                    "eo_ml": 1.5,
                    "eo_mr": 1.5,
                    "eo_mt": 1.5,
                    "eo_mb": 1.5,
                    "eo_hb": False,
                    "eo_bo": {
                        "ln_c2": {"clr_type": 0, "hclr_color": "#000000"},
                        "ln_w": 0,
                        "ln_s": 0
                    },
                    "eo_at": None,
                    "eo_ad": None,
                    "eo_rtd": "",
                    "eo_rtdf": {"rdf_ft": 0},
                    "i_bri": 0,
                    "i_cont": 0,
                    "i_opa": 1,
                    "i_clst": {"cv": {"op": "set", "opValue": []}},
                    "i_cid": blob['blob_id'],
                    "i_crop": {
                        "crop_oxr": 0,
                        "crop_oyr": 0,
                        "crop_wr": 1,
                        "crop_hr": 1,
                        "crop_rot": 0
                    },
                    "i_rot": 0,
                    "i_src": blob['image_url'],
                    "i_iw": False,
                    "i_iwc": {"iwc_w": False},
                    "i_msct": 0,
                    "i_pid": None
                }
            }

        return {
            "resolved": {
                "dsl_spacers": "*",
                "dsl_styleslices": [],
                "dsl_metastyleslices": [],
                "dsl_suggestedinsertions": {"sgsl_sugg": []},
                "dsl_suggesteddeletions": {"sgsl_sugg": []},
                "dsl_entitypositionmap": {"inline": entity_position_map},
                "dsl_entitymap": entity_map,
                "dsl_entitytypemap": entity_type_map,
                "dsl_drawingrevisionaccesstokenmap": {},
                "dsl_relateddocslices": {},
                "dsl_nestedmodelmap": {}
            },
            "autotext_content": {}
        }

    def _build_image_clip(self):
        image_urls = {}
        cosmo_ids = {}
        for blob in self.image_blobs:
            image_urls[blob['blob_id']] = blob['image_url']
            cosmo_ids[blob['blob_id']] = 1
        return {
            "image_urls": image_urls,
            "placeholder_ids": {},
            "cosmo_ids": cosmo_ids
        }

/* Label designer: one Alpine component. Talks to the Flask routes only. */
(function () {
    'use strict';

    var DEBOUNCE_MS = 250;
    var STATUS_MS = 15000;
    var NUDGE_MM = 0.5;
    var KEEP_ON_LABEL_MM = 1;
    var MIN_IMAGE_MM = 2;
    var DRAG_SLOP_PX = 4;
    var KEY_STOCK = 'ldx.stock';
    var KEY_FONT = 'ldx.font';
    var KEY_ORIENTATION = 'ldx.orientation';
    var KEY_THEME = 'ldx.theme';

    function storeGet(key) {
        try { return window.localStorage.getItem(key); } catch (e) { return null; }
    }

    function storeSet(key, value) {
        try { window.localStorage.setItem(key, value); } catch (e) { /* storage unavailable: forget */ }
    }

    function clamp(value, low, high) {
        return Math.min(high, Math.max(low, value));
    }

    function round2(value) {
        return Math.round(value * 100) / 100;
    }

    function jsonRequest(method, data) {
        return {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data === undefined ? {} : data)
        };
    }

    async function api(url, options) {
        var response;
        try {
            response = await fetch(url, options);
        } catch (e) {
            throw new Error('Cannot reach the label server - check the connection and try again.');
        }
        var body = null;
        try { body = await response.json(); } catch (e) { body = null; }
        if (!response.ok || (body && body.success === false)) {
            throw new Error((body && body.error) || ('Request failed (' + response.status + ')'));
        }
        return body;
    }

    function clone(value) {
        return JSON.parse(JSON.stringify(value));
    }

    function designer() {
        return {
            stocks: JSON.parse(document.getElementById('stocks-data').textContent),
            fonts: [],
            icons: [],
            defaultFont: '',
            doc: { label_size: '11354', orientation: 'landscape', copies: 1, name: '', blocks: [] },
            snapshot: '',
            editingId: null,
            selected: null,
            editing: null,
            editOriginal: '',
            drag: null,
            resize: null,
            rendered: { image: '', blocks: {} },
            renderError: '',
            rendering: false,
            busy: false,
            gen: 0,
            modal: null,
            seq: 0,
            timer: null,
            stageW: 600,
            winH: window.innerHeight,
            counter: 0,
            theme: 'light',
            orientationChosen: false,
            printer: { ok: true, text: 'Printer ...', detail: '' },
            toasts: [],
            toastSeq: 0,
            history: {
                open: true, q: '', sort: 'last_printed', starred: false,
                labels: [], selected: [], loading: false, error: '', seq: 0, timer: null
            },

            /* ---- lifecycle ---- */

            init: function () {
                var self = this;
                var keys = Object.keys(this.stocks);
                var stock = storeGet(KEY_STOCK);
                this.doc.label_size = this.stocks[stock] ? stock : (this.stocks['11354'] ? '11354' : keys[0]);
                var orientation = storeGet(KEY_ORIENTATION);
                this.orientationChosen = orientation === 'portrait' || orientation === 'landscape';
                this.doc.orientation = this.orientationChosen ? orientation : this.shapeOf(this.doc.label_size);

                var theme = storeGet(KEY_THEME);
                if (theme !== 'dark' && theme !== 'light') {
                    theme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                }
                this.setTheme(theme);

                this.snapshot = JSON.stringify(this.doc);
                this.$watch('doc', function () { self.schedule(); });

                if (window.ResizeObserver) {
                    new ResizeObserver(function (entries) {
                        self.stageW = entries[0].contentRect.width || self.stageW;
                    }).observe(this.$refs.stage);
                }
                this.stageW = this.$refs.stage.clientWidth || this.stageW;
                window.addEventListener('resize', function () {
                    self.winH = window.innerHeight;
                    self.stageW = self.$refs.stage.clientWidth || self.stageW;
                });

                window.addEventListener('beforeunload', function (event) {
                    if (self.dirty) {
                        event.preventDefault();
                        event.returnValue = '';
                    }
                });

                this.loadFonts();
                this.loadIcons();
                this.loadHistory();
                this.pollStatus();
                setInterval(function () { self.pollStatus(); }, STATUS_MS);
                this.renderNow();
            },

            async loadFonts() {
                try {
                    this.fonts = await api('/fonts');
                } catch (e) {
                    this.fonts = [];
                }
                var remembered = storeGet(KEY_FONT);
                var names = this.fonts.map(function (f) { return f.family; });
                if (remembered && names.indexOf(remembered) >= 0) {
                    this.defaultFont = remembered;
                } else if (names.indexOf('DejaVu Sans') >= 0) {
                    this.defaultFont = 'DejaVu Sans';
                } else {
                    this.defaultFont = names[0] || 'DejaVu Sans';
                }
            },

            async loadIcons() {
                try { this.icons = await api('/icons'); } catch (e) { this.icons = []; }
            },

            /* ---- geometry ---- */

            shapeOf: function (key) {
                var s = this.stocks[key];
                return s.width_mm <= s.height_mm ? 'portrait' : 'landscape';
            },

            get canvasW() {
                var s = this.stocks[this.doc.label_size];
                var short = Math.min(s.width_mm, s.height_mm), long = Math.max(s.width_mm, s.height_mm);
                return this.doc.orientation === 'portrait' ? short : long;
            },

            get canvasH() {
                var s = this.stocks[this.doc.label_size];
                var short = Math.min(s.width_mm, s.height_mm), long = Math.max(s.width_mm, s.height_mm);
                return this.doc.orientation === 'portrait' ? long : short;
            },

            get frameW() {
                var avail = Math.max(120, this.stageW - 16);
                var maxH = Math.max(200, Math.min(this.winH * 0.6, 460));
                return Math.floor(Math.min(avail, maxH * this.canvasW / this.canvasH));
            },

            get ppm() {
                return this.frameW / this.canvasW;
            },

            frameStyle: function () {
                return 'width:' + this.frameW + 'px;height:' + Math.round(this.frameW * this.canvasH / this.canvasW) +
                    'px;border-radius:' + (2 * this.ppm).toFixed(1) + 'px';
            },

            info: function (id) {
                return this.rendered.blocks[id] || null;
            },

            /* ---- document ---- */

            payload: function () {
                return clone(this.doc);
            },

            get dirty() {
                return JSON.stringify(this.doc) !== this.snapshot;
            },

            defaultName: function () {
                for (var i = 0; i < this.doc.blocks.length; i++) {
                    var b = this.doc.blocks[i];
                    if (b.type !== 'text') { continue; }
                    var lines = (b.text || '').split('\n').map(function (l) { return l.trim(); });
                    var first = lines.filter(Boolean)[0];
                    if (first) { return first.slice(0, 60); }
                }
                return 'Untitled';
            },

            blockLabel: function (b) {
                if (b.type === 'text') {
                    var first = (b.text || '').split('\n').map(function (l) { return l.trim(); }).filter(Boolean)[0];
                    return 'Text: ' + (first ? first.slice(0, 24) : '(empty)');
                }
                return 'Image: ' + String(b.src).replace(/^(icon|upload):/, '').slice(0, 24);
            },

            nextId: function () {
                var self = this;
                this.doc.blocks.forEach(function (b) {
                    var m = /^b(\d+)$/.exec(b.id);
                    if (m) { self.counter = Math.max(self.counter, parseInt(m[1], 10)); }
                });
                this.counter += 1;
                return 'b' + this.counter;
            },

            current: function () {
                var id = this.selected;
                return this.doc.blocks.find(function (b) { return b.id === id; }) || null;
            },

            select: function (id) {
                if (this.editing && this.editing !== id) { this.commitEdit(); }
                this.selected = id;
            },

            deselect: function () {
                this.commitEdit();
                this.selected = null;
            },

            nextY: function () {
                if (!this.doc.blocks.length) { return null; }
                var self = this, bottom = 0;
                this.doc.blocks.forEach(function (b) {
                    var i = self.info(b.id);
                    if (i) { bottom = Math.max(bottom, i.bbox_mm[1] + i.bbox_mm[3]); }
                });
                return round2(clamp(bottom + 1, 0, Math.max(0, this.canvasH - 6)));
            },

            addText: function () {
                var block = {
                    type: 'text', id: this.nextId(), text: 'Text', x_mm: 2, y_mm: this.nextY(), width_mm: null,
                    align: 'center', font_family: this.defaultFont || 'DejaVu Sans', font_size_pt: 14,
                    bold: false, italic: false, underline: false, shrink_to_fit: false
                };
                this.doc.blocks.push(block);
                this.selected = block.id;
            },

            addImage: function (src) {
                var width = round2(Math.min(20, this.canvasW / 2));
                var y = this.nextY();
                if (y === null || y + width > this.canvasH - 1) {
                    // no room below the other blocks: start at the top, small enough to stay on the label
                    y = 2;
                    width = round2(Math.max(MIN_IMAGE_MM, Math.min(width, this.canvasH - 4)));
                }
                var block = {
                    type: 'image', id: this.nextId(), src: src, x_mm: 2, y_mm: y,
                    width_mm: width, mono: 'threshold', threshold: 128
                };
                this.doc.blocks.push(block);
                this.selected = block.id;
            },

            async onUpload(event) {
                var input = event.target;
                var file = input.files && input.files[0];
                if (!file) { return; }
                var form = new FormData();
                form.append('file', file);
                try {
                    var body = await api('/images', { method: 'POST', body: form });
                    this.addImage(body.ref);
                } catch (e) {
                    this.toast('error', 'Upload failed: ' + e.message);
                } finally {
                    input.value = '';
                }
            },

            moveBlock: function (index, delta) {
                var to = index + delta;
                if (to < 0 || to >= this.doc.blocks.length) { return; }
                var moved = this.doc.blocks.splice(index, 1)[0];
                this.doc.blocks.splice(to, 0, moved);
            },

            removeBlock: function (id) {
                if (this.editing === id) { this.editing = null; }
                if (this.selected === id) { this.selected = null; }
                this.doc.blocks = this.doc.blocks.filter(function (b) { return b.id !== id; });
            },

            newLabel: function () {
                if (this.busy) { return; }
                this.guardUnsaved('Start a new label?', 'New label', this.doNew.bind(this));
            },

            doNew: function () {
                this.gen += 1;
                this.editingId = null;
                this.selected = null;
                this.editing = null;
                this.doc = {
                    label_size: this.doc.label_size, orientation: this.doc.orientation,
                    copies: 1, name: '', blocks: []
                };
                this.snapshot = JSON.stringify(this.doc);
            },

            setCopies: function (value, el) {
                var n = parseInt(value, 10);
                if (!isFinite(n)) { n = this.doc.copies; }
                this.doc.copies = clamp(n, 1, 99);
                if (el) { el.value = this.doc.copies; }
            },

            onStockChange: function () {
                storeSet(KEY_STOCK, this.doc.label_size);
                if (!this.orientationChosen) { this.doc.orientation = this.shapeOf(this.doc.label_size); }
            },

            toggleOrientation: function () {
                this.doc.orientation = this.doc.orientation === 'portrait' ? 'landscape' : 'portrait';
                this.orientationChosen = true;
                storeSet(KEY_ORIENTATION, this.doc.orientation);
            },

            setTheme: function (theme) {
                this.theme = theme;
                document.documentElement.setAttribute('data-theme', theme);
            },

            toggleTheme: function () {
                this.setTheme(this.theme === 'dark' ? 'light' : 'dark');
                storeSet(KEY_THEME, this.theme);
            },

            /* ---- confirmation dialog (in-page, never window.confirm) ---- */

            askConfirm: function (title, text, confirm, action) {
                this.modal = { title: title, text: text, confirm: confirm, action: action };
                var self = this;
                this.$nextTick(function () {
                    var b = self.$refs.modalCancel;
                    if (b) { b.focus(); }
                });
            },

            closeModal: function () {
                this.modal = null;
            },

            acceptModal: function () {
                var action = this.modal && this.modal.action;
                this.modal = null;
                if (action) { action(); }
            },

            trapTab: function (event) {
                var box = this.$refs.modalBox;
                var items = box ? box.querySelectorAll('button') : [];
                if (!items.length) { return; }
                var first = items[0], last = items[items.length - 1];
                if (event.shiftKey && document.activeElement === first) {
                    event.preventDefault();
                    last.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                    event.preventDefault();
                    first.focus();
                }
            },

            guardUnsaved: function (title, confirm, action) {
                if (!this.dirty) { action(); return; }
                this.askConfirm(title, 'This label has unsaved changes that would be lost.', confirm + ' anyway', action);
            },

            /* ---- inspector helpers ---- */

            fontChoices: function (block) {
                var known = this.fonts.some(function (f) { return f.family === block.font_family; });
                return known ? this.fonts : [{ family: block.font_family, styles: [] }].concat(this.fonts);
            },

            styleOk: function (block, style) {
                var f = this.fonts.find(function (x) { return x.family === block.font_family; });
                if (!f) { return true; }
                return f.styles.indexOf(style) >= 0 || f.styles.indexOf('bold-italic') >= 0;
            },

            onFontChange: function () {
                var b = this.current();
                if (!b) { return; }
                if (!this.styleOk(b, 'bold')) { b.bold = false; }
                if (!this.styleOk(b, 'italic')) { b.italic = false; }
                this.defaultFont = b.font_family;
                this.rememberFont();
            },

            rememberFont: function () {
                storeSet(KEY_FONT, this.defaultFont);
            },

            substituted: function (b) {
                var i = this.info(b.id);
                return !!(i && i.font_substituted);
            },

            fontCap: function () {
                var s = this.stocks[this.doc.label_size];
                return Math.floor(Math.max(s.width_mm, s.height_mm) * 72 / 25.4);
            },

            setSize: function (value, el) {
                var b = this.current();
                var n = parseFloat(value);
                if (b && isFinite(n)) { b.font_size_pt = clamp(n, 1, this.fontCap()); }
                if (el && b) { el.value = b.font_size_pt; }
            },

            setBoxWidth: function (value, el) {
                var b = this.current();
                if (!b) { return; }
                var n = parseFloat(value);
                b.width_mm = isFinite(n) ? round2(clamp(n, 1, this.canvasW)) : null;
                if (el) { el.value = b.width_mm === null ? '' : b.width_mm; }
            },

            maxImageWidth: function (b) {
                var i = this.info(b.id);
                var aspect = i && i.bbox_mm[2] > 0 ? i.bbox_mm[3] / i.bbox_mm[2] : 1;
                var room = Math.min(this.canvasW - Math.max(0, b.x_mm), (this.canvasH - Math.max(0, b.y_mm)) / aspect);
                return Math.max(MIN_IMAGE_MM, Math.min(this.canvasW, room));
            },

            setImageWidth: function (b, value, el) {
                var n = parseFloat(value);
                if (isFinite(n)) { b.width_mm = round2(clamp(n, MIN_IMAGE_MM, this.maxImageWidth(b))); }
                if (el) { el.value = b.width_mm; }
            },

            problems: function () {
                var out = [], self = this;
                this.doc.blocks.forEach(function (b) {
                    var i = self.info(b.id);
                    if (!i) { return; }
                    var name = self.blockLabel(b);
                    if (i.overflow) {
                        out.push({ key: b.id + 'o', kind: 'error',
                            text: name + ' does not fit on the label - move it, shorten it, or turn on shrink to fit.' });
                    }
                    if (i.missing) {
                        out.push({ key: b.id + 'm', kind: 'error', text: name + ' - the image file is missing.' });
                    }
                    if (i.font_substituted) {
                        out.push({ key: b.id + 's', kind: 'note', text: name + ' - font not installed, a substitute is used.' });
                    }
                });
                return out;
            },

            /* ---- render ---- */

            schedule: function () {
                var self = this;
                clearTimeout(this.timer);
                this.timer = setTimeout(function () { self.renderNow(); }, DEBOUNCE_MS);
            },

            async renderNow() {
                clearTimeout(this.timer);
                var seq = ++this.seq;
                this.rendering = true;
                try {
                    var body = await api('/render', jsonRequest('POST', this.payload()));
                    if (seq !== this.seq) { return; }
                    var byId = {};
                    body.blocks.forEach(function (b) { byId[b.id] = b; });
                    this.rendered = { image: body.image, blocks: byId };
                    this.renderError = '';
                } catch (e) {
                    if (seq === this.seq) { this.renderError = this.nameBlocks(e.message); }
                } finally {
                    if (seq === this.seq) { this.rendering = false; }
                }
            },

            nameBlocks: function (message) {
                var self = this;
                return String(message).replace(/\bblock (b\d+): /, function (all, id) {
                    var b = self.doc.blocks.find(function (x) { return x.id === id; });
                    return (b ? self.blockLabel(b) : 'Block ' + id) + ': ';
                });
            },

            /* ---- on-label overlays ---- */

            overlayClass: function (b) {
                var i = this.info(b.id) || {};
                return {
                    selected: this.selected === b.id,
                    overflow: !!i.overflow,
                    missing: !!i.missing,
                    pending: !i.bbox_mm,
                    image: b.type === 'image',
                    editing: this.editing === b.id
                };
            },

            boxPx: function (b) {
                var i = this.info(b.id);
                if (!i) { return null; }
                var p = this.ppm;
                return {
                    left: i.bbox_mm[0] * p, top: i.bbox_mm[1] * p,
                    width: Math.max(i.bbox_mm[2] * p, 6), height: Math.max(i.bbox_mm[3] * p, 6)
                };
            },

            overlayStyle: function (b) {
                var r = this.boxPx(b);
                if (!r) { return 'display:none'; }
                return 'left:' + r.left.toFixed(1) + 'px;top:' + r.top.toFixed(1) + 'px;width:' +
                    r.width.toFixed(1) + 'px;height:' + r.height.toFixed(1) + 'px';
            },

            inplaceStyle: function () {
                var b = this.doc.blocks.find(function (x) { return x.id === this.editing; }, this);
                if (!b) { return 'display:none'; }
                var r = this.boxPx(b);
                if (!r) { return 'display:none'; }
                var size = Math.max(12, b.font_size_pt * 25.4 / 72 * this.ppm);
                return 'left:' + r.left.toFixed(1) + 'px;top:' + r.top.toFixed(1) + 'px;min-width:' +
                    Math.max(r.width, 60).toFixed(1) + 'px;min-height:' + Math.max(r.height, size * 1.3).toFixed(1) +
                    'px;font-size:' + size.toFixed(1) + 'px;text-align:' + b.align;
            },

            startEdit: function (b) {
                if (b.type !== 'text') { return; }
                this.selected = b.id;
                this.editing = b.id;
                this.editOriginal = b.text;
                var self = this;
                this.$nextTick(function () {
                    var ta = self.$refs.inplace;
                    ta.focus();
                    ta.setSelectionRange(ta.value.length, ta.value.length);
                });
            },

            onInplaceInput: function (event) {
                var b = this.doc.blocks.find(function (x) { return x.id === this.editing; }, this);
                if (b) { b.text = event.target.value; }
            },

            commitEdit: function (refocus) {
                var id = this.editing;
                this.editing = null;
                if (refocus && id) { this.focusOverlay(id); }
            },

            focusOverlay: function (id) {
                var self = this;
                this.$nextTick(function () {
                    var el = self.$refs.frame.querySelector('[data-block="' + id + '"]');
                    if (el) { el.focus(); }
                });
            },

            onInplaceBlur: function (event) {
                this.commitEdit(!event.relatedTarget);
            },

            cancelEdit: function () {
                var b = this.doc.blocks.find(function (x) { return x.id === this.editing; }, this);
                if (b) { b.text = this.editOriginal; }
                this.editing = null;
                var el = this.$refs.frame.querySelector('[data-block="' + (b ? b.id : '') + '"]');
                if (el) { el.focus(); }
            },

            limits: function (box) {
                return {
                    xMin: KEEP_ON_LABEL_MM - box[2], xMax: this.canvasW - KEEP_ON_LABEL_MM,
                    yMin: KEEP_ON_LABEL_MM - box[3], yMax: this.canvasH - KEEP_ON_LABEL_MM
                };
            },

            freezeWidth: function (b) {
                var i = this.info(b.id);
                if (b.type === 'text' && (b.width_mm === null || b.width_mm === undefined) && i) {
                    b.width_mm = round2(i.bbox_mm[2]);
                }
            },

            startX: function (b, box) { return b.x_mm === undefined || b.x_mm === null ? box[0] : b.x_mm; },
            startY: function (b, box) { return b.y_mm === undefined || b.y_mm === null ? box[1] : b.y_mm; },

            startDrag: function (event, b) {
                if (event.button !== 0 && event.pointerType === 'mouse') { return; }
                var i = this.info(b.id);
                if (!i) { return; }
                this.select(b.id);
                this.drag = {
                    id: b.id, sx: event.clientX, sy: event.clientY, moved: false,
                    box: i.bbox_mm.slice(), x0: this.startX(b, i.bbox_mm), y0: this.startY(b, i.bbox_mm)
                };
                event.currentTarget.setPointerCapture(event.pointerId);
            },

            onDrag: function (event) {
                var d = this.drag;
                if (!d) { return; }
                var dx = event.clientX - d.sx, dy = event.clientY - d.sy;
                if (!d.moved && Math.hypot(dx, dy) < DRAG_SLOP_PX) { return; }
                var b = this.doc.blocks.find(function (x) { return x.id === d.id; });
                if (!b) { return; }
                if (!d.moved) { this.freezeWidth(b); d.box = this.info(b.id).bbox_mm.slice(); }
                d.moved = true;
                this.applyMove(b, d, d.x0 + dx / this.ppm, d.y0 + dy / this.ppm);
            },

            applyMove: function (b, d, x, y) {
                var l = this.limits(d.box);
                var nx = round2(clamp(x, l.xMin, l.xMax)), ny = round2(clamp(y, l.yMin, l.yMax));
                var i = this.info(b.id);
                if (i) {
                    i.bbox_mm = [d.box[0] + (nx - d.x0), d.box[1] + (ny - d.y0), d.box[2], d.box[3]];
                }
                b.x_mm = nx;
                b.y_mm = ny;
            },

            endDrag: function (event) {
                var d = this.drag;
                if (!d) { return; }
                this.drag = null;
                try { event.currentTarget.releasePointerCapture(event.pointerId); } catch (e) { /* already released */ }
                if (!d.moved) {
                    var b = this.doc.blocks.find(function (x) { return x.id === d.id; });
                    if (b) { this.startEdit(b); }
                }
            },

            nudge: function (b, dx, dy) {
                var i = this.info(b.id);
                if (!i) { return; }
                this.freezeWidth(b);
                var box = i.bbox_mm.slice();
                var d = { box: box, x0: this.startX(b, box), y0: this.startY(b, box) };
                this.applyMove(b, d, d.x0 + dx, d.y0 + dy);
            },

            startResize: function (event, b) {
                var i = this.info(b.id);
                if (!i) { return; }
                this.resize = { id: b.id, sx: event.clientX, w0: b.width_mm, box: i.bbox_mm.slice(), max: this.maxImageWidth(b) };
                event.currentTarget.setPointerCapture(event.pointerId);
            },

            onResize: function (event) {
                var r = this.resize;
                if (!r) { return; }
                var b = this.doc.blocks.find(function (x) { return x.id === r.id; });
                if (!b) { return; }
                var w = round2(clamp(r.w0 + (event.clientX - r.sx) / this.ppm, MIN_IMAGE_MM, r.max));
                b.width_mm = w;
                var i = this.info(b.id);
                if (i && r.box[2] > 0) {
                    var k = w / r.w0;
                    i.bbox_mm = [r.box[0], r.box[1], r.box[2] * k, r.box[3] * k];
                }
            },

            endResize: function (event) {
                if (!this.resize) { return; }
                this.resize = null;
                try { event.currentTarget.releasePointerCapture(event.pointerId); } catch (e) { /* already released */ }
            },

            /* ---- keyboard ---- */

            onKey: function (event) {
                if (this.modal) { return; }
                var mod = event.ctrlKey || event.metaKey;
                if (mod && event.key === 'Enter') {
                    event.preventDefault();
                    this.print();
                    return;
                }
                if (mod && (event.key === 'p' || event.key === 'P')) {
                    event.preventDefault();
                    this.renderNow();
                    return;
                }
                var arrows = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
                var step = arrows[event.key];
                if (!step || mod || event.altKey || !this.selected || this.editing) { return; }
                var t = event.target;
                var onBody = t === document.body || t === document.documentElement;
                var onOverlay = t && t.classList && t.classList.contains('overlay');
                if (!onBody && !onOverlay) { return; }
                var b = this.current();
                if (!b) { return; }
                event.preventDefault();
                this.nudge(b, step[0] * NUDGE_MM, step[1] * NUDGE_MM);
            },

            /* ---- save / print ---- */

            afterSave: function (label, sent, gen) {
                if (gen !== this.gen) { return; }  // the user opened or started another label meanwhile
                var named = Object.assign({}, sent);
                if (label && label.id) {
                    this.editingId = label.id;
                    if (!named.name) { named.name = label.name; }
                    if (!this.doc.name) { this.doc.name = label.name; }
                }
                this.snapshot = JSON.stringify(named);
            },

            commitActiveField: function () {
                var a = document.activeElement;
                if (a && (a.tagName === 'INPUT' || a.tagName === 'SELECT' || a.tagName === 'TEXTAREA')) {
                    a.dispatchEvent(new Event('change', { bubbles: true }));
                }
            },

            async save() {
                if (this.busy) { return; }
                this.commitActiveField();
                this.busy = true;
                var gen = this.gen, sent = this.payload(), id = this.editingId;
                try {
                    var body = id
                        ? await api('/labels/' + encodeURIComponent(id), jsonRequest('PUT', { doc: sent }))
                        : await api('/labels', jsonRequest('POST', { doc: sent }));
                    this.afterSave(body.label, sent, gen);
                    this.toast('success', 'Saved "' + (body.label.name || 'label') + '"');
                    this.loadHistory();
                } catch (e) {
                    this.noteMissing(e);
                    this.toast('error', 'Save failed: ' + e.message);
                } finally {
                    this.busy = false;
                }
            },

            async print() {
                if (this.busy) { return; }
                this.commitEdit();
                this.commitActiveField();
                this.busy = true;
                var gen = this.gen, sent = this.payload();
                try {
                    var data = { doc: sent, copies: sent.copies };
                    if (this.editingId) { data.id = this.editingId; }
                    var body = await api('/print', jsonRequest('POST', data));
                    this.afterSave(body.label, sent, gen);
                    var n = sent.copies;
                    this.toast('success', 'Sent ' + n + (n === 1 ? ' copy' : ' copies') + ' to the printer');
                    if (body.warning) { this.toast('warning', body.warning); }
                    this.loadHistory();
                } catch (e) {
                    this.noteMissing(e);
                    this.toast('error', 'Print failed: ' + e.message);
                } finally {
                    this.busy = false;
                }
            },

            noteMissing: function (e) {
                if (this.editingId && /not found/i.test(e.message)) { this.editingId = null; }
            },

            /* ---- status and toasts ---- */

            async pollStatus() {
                try {
                    var s = await api('/status');
                    if (s.error) {
                        this.printer = { ok: false, text: 'Printer error', detail: String(s.error) };
                        return;
                    }
                    var raw = s.state !== undefined ? s.state : s['printer-state'];
                    var state = { 3: 'idle', 4: 'printing', 5: 'stopped' }[raw] || String(raw === undefined ? 'ready' : raw);
                    var stopped = state === 'stopped';
                    this.printer = {
                        ok: !stopped, text: stopped ? 'Printer stopped' : 'Printer ' + state,
                        detail: s['printer-state-message'] || ''
                    };
                } catch (e) {
                    this.printer = { ok: false, text: 'Printer unreachable', detail: e.message };
                }
            },

            toast: function (kind, text) {
                var self = this;
                var id = ++this.toastSeq;
                this.toasts.push({ id: id, kind: kind, text: text });
                if (this.toasts.length > 4) { this.toasts.shift(); }
                setTimeout(function () { self.dismiss(id); }, kind === 'error' ? 9000 : 5000);
            },

            dismiss: function (id) {
                this.toasts = this.toasts.filter(function (t) { return t.id !== id; });
            },

            /* ---- history ---- */

            toggleHistory: function () {
                this.history.open = !this.history.open;
            },

            scheduleHistory: function () {
                var self = this;
                clearTimeout(this.history.timer);
                this.history.timer = setTimeout(function () { self.loadHistory(); }, DEBOUNCE_MS);
            },

            async loadHistory() {
                clearTimeout(this.history.timer);
                var h = this.history;
                var seq = ++h.seq;
                h.loading = true;
                var qs = 'sort=' + encodeURIComponent(h.sort);
                if (h.q.trim()) { qs += '&q=' + encodeURIComponent(h.q.trim()); }
                if (h.starred) { qs += '&starred=1'; }
                try {
                    var body = await api('/labels?' + qs);
                    if (seq !== h.seq) { return; }
                    h.labels = body.labels;
                    var ids = body.labels.map(function (l) { return l.id; });
                    h.selected = h.selected.filter(function (id) { return ids.indexOf(id) >= 0; });
                    h.error = '';
                } catch (e) {
                    if (seq === h.seq) { h.error = 'Could not load saved labels: ' + e.message; }
                } finally {
                    if (seq === h.seq) { h.loading = false; }
                }
            },

            thumbUrl: function (l) {
                return '/labels/' + encodeURIComponent(l.id) + '/thumbnail.png?v=' + encodeURIComponent(l.updated_at);
            },

            lastPrinted: function (l) {
                if (!l.last_printed_at) { return 'Never printed'; }
                var d = new Date(l.last_printed_at);
                return 'Printed ' + (isNaN(d.getTime()) ? l.last_printed_at : d.toLocaleString());
            },

            allSelected: function () {
                return this.history.labels.length > 0 && this.history.selected.length === this.history.labels.length;
            },

            toggleAll: function (checked) {
                this.history.selected = checked ? this.history.labels.map(function (l) { return l.id; }) : [];
            },

            toggleOne: function (id, checked) {
                var rest = this.history.selected.filter(function (x) { return x !== id; });
                this.history.selected = checked ? rest.concat([id]) : rest;
            },

            async toggleStar(l) {
                try {
                    await api('/labels/' + encodeURIComponent(l.id) + '/star', jsonRequest('PUT', { starred: !l.starred }));
                    await this.loadHistory();
                } catch (e) {
                    this.toast('error', 'Could not change the star: ' + e.message);
                }
            },

            openLabel: function (l) {
                if (this.busy) { return; }
                this.guardUnsaved('Open "' + this.nm(l) + '"?', 'Open', this.doOpen.bind(this, l));
            },

            nm: function (l) {
                return l.name || 'Untitled';
            },

            doOpen: function (l) {
                this.gen += 1;
                this.editing = null;
                this.selected = null;
                this.doc = {
                    label_size: l.label_size, orientation: l.orientation, copies: l.copies,
                    name: l.name, blocks: clone(l.blocks)
                };
                this.editingId = l.id;
                this.snapshot = JSON.stringify(this.doc);
                this.rendered = { image: this.rendered.image, blocks: {} };
                this.renderNow();
                this.toast('info', 'Opened "' + this.nm(l) + '"');
            },

            async duplicateLabel(l) {
                try {
                    var body = await api('/labels/' + encodeURIComponent(l.id) + '/duplicate', jsonRequest('POST', {}));
                    this.toast('success', 'Duplicated "' + this.nm(body.label) + '"');
                    await this.loadHistory();
                } catch (e) {
                    this.toast('error', 'Duplicate failed: ' + e.message);
                }
            },

            async reprint(l) {
                try {
                    var body = await api('/labels/' + encodeURIComponent(l.id) + '/print', jsonRequest('POST', {}));
                    this.toast('success', 'Re-printed "' + this.nm(l) + '"');
                    if (body.warning) { this.toast('warning', body.warning); }
                    await this.loadHistory();
                } catch (e) {
                    this.toast('error', 'Re-print failed: ' + e.message);
                }
            },

            deleteSelected: function () {
                var ids = this.history.selected.slice();
                if (!ids.length) { return; }
                var n = ids.length;
                this.askConfirm('Delete ' + n + (n === 1 ? ' label?' : ' labels?'),
                    'The selected ' + (n === 1 ? 'label' : n + ' labels') + ' will be removed from the history. This cannot be undone.',
                    'Delete ' + n, this.doDelete.bind(this, ids));
            },

            async doDelete(ids) {
                try {
                    var body = await api('/labels', jsonRequest('DELETE', { ids: ids }));
                    if (ids.indexOf(this.editingId) >= 0) { this.editingId = null; }
                    this.history.selected = [];
                    this.toast('success', 'Deleted ' + body.deleted + (body.deleted === 1 ? ' label' : ' labels'));
                    await this.loadHistory();
                } catch (e) {
                    this.toast('error', 'Delete failed: ' + e.message);
                }
            }
        };
    }

    document.addEventListener('alpine:init', function () {
        window.Alpine.data('designer', designer);
    });
}());

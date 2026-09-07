# Agent 2 — The Document Layout Agent

### Agent 2 — The Document Layout Agent

*Turns a PDF or scanned image into a typed tree of semantic regions.*

#### The Problem

Most enterprise agent work begins with a document the agent didn't generate. The native form — pages of mixed text, tables, figures, headers, footnotes, stamps, signatures, multi-column layouts, footers that change mid-document, tables that span pages — is unusable as a context input.

Pasting the [OCR output](https://en.wikipedia.org/wiki/Optical_character_recognition) into a prompt gets the agent to produce something, but the output is bad in subtle ways: it treats footers as content, it loses table structure, it merges columns, it conflates section headings with body text.

The general problem is that **a document is not a string**. It's a tree of typed regions with explicit spatial and semantic relationships. Pretending it is a string throws away the structure the downstream policy needs to be reliable.

#### Why Naïve Approaches Fail.

- 

*"Just run OCR and concatenate the text."* Loses table structure, loses multi-column ordering, conflates headers with body, includes irrelevant marginalia, and produces output whose meaning depends on the OCR engine's ordering heuristics rather than on the document's actual structure.

- 

*"Send the page images directly to a vision-language model."* Works for single-page documents and small batches, but costs explode on real corpora. The model also makes its own (often wrong) decisions about what to extract. Without a structured intermediate representation, you can't audit or verify.

- 

*"Use a generic PDF library."* PDFs aren't a documented structured format. They're a layout-instruction language. Two PDFs that look identical can have wildly different internal structures, and most libraries produce output that's approximately the text in approximately the order it was typeset.

#### The Mechanism

The layout agent runs a document through a layout-detection model, segments it into typed regions (heading, paragraph, table-cell, figure-caption, signature-block, footer, header), runs OCR per region with confidence-aware re-runs on low-confidence regions. It then reconstructs tables as row-and-column structures, links continued headers and tables across pages, and emits a hierarchical region graph that downstream patterns can navigate.

The output is a tree, not a flat text blob. The tree preserves spatial relationships that pure OCR throws away (a table cell knows it is in column 3, row 5, of the table titled "Q2 Revenue by Region"). Every region carries its source bounding box and page number, so downstream provenance can point at the exact pixels.

![Pattern 026 — Agent 2 — The Document Layout Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dcaa90f3d34d7e2aa32_codex-pattern-026-agent-2-the-document-layout-agent-the-mechanism.png)

```python
# perception/document_layout.py
from dataclasses import dataclass, field
from typing import Literal

RegionType = Literal[
    "heading", "subheading", "paragraph", "table", "table_cell",
    "figure", "figure_caption", "signature", "stamp",
    "header", "footer", "page_number", "footnote"
]

@dataclass
class DocumentRegion:
    id: str
    type: RegionType
    page: int
    bbox: tuple[float, float, float, float]
    text: str
    ocr_confidence: float
    children: list["DocumentRegion"] = field(default_factory=list)
    parent_id: str | None = None
    # Table-specific
    table_row: int | None = None
    table_col: int | None = None
    table_header: bool = False

@dataclass
class DocumentTree:
    document_id: str
    pages: int
    root: DocumentRegion       # synthetic root containing top-level regions
    
    def regions_of_type(self, t: RegionType) -> list[DocumentRegion]:
        out = []
        def walk(r):
            if r.type == t:
                out.append(r)
            for c in r.children:
                walk(c)
        walk(self.root)
        return out
    
    def find_by_text(self, query: str) -> list[DocumentRegion]:
        return [r for r in self._flat() if query in r.text]

class DocumentLayoutAgent:
    def __init__(self, layout_detector, ocr, table_reconstructor,
                 *, low_conf_threshold: float = 0.7):
        self.layout = layout_detector
        self.ocr = ocr
        self.tables = table_reconstructor
        self.low_conf = low_conf_threshold
    
    def parse(self, pdf_bytes: bytes) -> DocumentTree:
        pages = self._rasterize(pdf_bytes)
        all_regions = []
        for page_num, page_img in enumerate(pages):
            regions = self.layout.detect(page_img)           # 1. Layout detection
            for region in regions:
                text, conf = self.ocr.read(page_img, region.bbox)  # 2. OCR
                if conf < self.low_conf:
                    # Re-run with a higher-quality OCR setting
                    text, conf = self.ocr.read(page_img, region.bbox, mode="quality")
                region.text = text
                region.ocr_confidence = conf
                if region.type == "table":
                    region.children = self.tables.reconstruct(  # 3. Table reconstruction
                        page_img, region.bbox)
            all_regions.append((page_num, regions))
        
        root = self._build_tree(all_regions)                 # 4. Cross-page linking
        return DocumentTree(
            document_id=self._hash(pdf_bytes),
            pages=len(pages),
            root=root,
        )
    
    def _build_tree(self, regions_by_page):
        """Cross-page linking: continued tables, repeated headers, etc."""
        root = DocumentRegion(id="root", type="paragraph", page=-1,
                              bbox=(0,0,0,0), text="", ocr_confidence=1.0)
        # Group headings into sections; link continued tables across pages.
        current_section = root
        for page_num, regions in regions_by_page:
            for r in regions:
                if r.type in ("header", "footer", "page_number"):
                    continue  # drop chrome
                if r.type == "heading":
                    current_section = r
                    root.children.append(r)
                else:
                    r.parent_id = current_section.id
                    current_section.children.append(r)
        return root
```

#### Trade-offs and Alternatives

This pattern is expensive. A real layout-detection model plus OCR plus table reconstruction is ten to a hundred times the cost of plain OCR.

The cost is justified for documents that flow downstream into agents that need structure: anything that needs to cite a specific table cell, know whether a phrase is in a heading or a body paragraph, or ignore footers.

For one-shot extractions over simple documents, plain OCR (or even direct vision-language extraction) is fine. The pattern earns its cost when documents flow into multiple downstream consumers, the same document is queried repeatedly, or provenance to specific regions is required.

#### Production failure modes

- 

**Layout-detector bias:** Layout detectors trained on academic papers misclassify business documents (treats a sidebar as a footnote, mis-segments multi-column invoices). Detect by sampling outputs and reviewing against ground truth, and mitigate by training a layout head on documents from your actual distribution.

- 

**OCR-confidence calibration:** Modern OCR engines often report high confidence on text that's wrong because the input is unusual. Mitigate by running a second, different OCR engine on a sample and comparing. Significant disagreement is a flag.

- 

**Table reconstruction degeneracy:** Tables with merged cells, nested headers, or rotated text break most reconstructors. Mitigate by detecting non-rectangular tables and falling back to per-cell extraction with explicit "unstructured" flagging downstream.

- 

**Cross-page linking failure:** Tables continued across page breaks are linked as separate tables. The resulting downstream queries return only half the data. Mitigate by linking on table-title repetition and column-header signature.

#### Case Study

An underwriting workflow at a specialty insurer ingests submission packets. It's typically forty pages of mixed loss runs, schedules, broker memos, and supplementary attachments. This produces a structured submission record without a human in the loop until exception.

The Document Layout Agent emits a region tree per submission. Downstream agents (a Schema-Inference Agent over the loss runs, a Symbolic-Neural Bridge translating broker narratives into structured exposure summaries, a Provenance Tracker attaching every entry in the final record back to its source region) compose into a workflow that handled 73% of submissions end-to-end after six months of tuning, with a measured one-shot accuracy on extracted fields of 96% measured against expert-reviewed ground truth.

**Pairs with:** Schema-Inference (Agent 7), Provenance Tracker (Agent 55), Multimodal Grounding (Agent 1).

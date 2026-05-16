# Document AI — ML

Train and evaluate models for card OCR, payor classification, and SBC parsing.

## Train
```
just train.card_ocr       # LayoutLMv3 fine-tune
just train.payor          # ResNet-50 fine-tune
just train.sbc            # LayoutLMv3 for SBC
```

## Evaluate
```
just eval.card_ocr
```

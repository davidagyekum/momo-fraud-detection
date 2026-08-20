import { useMutation, useQuery } from "@tanstack/react-query";
import { Image } from "expo-image";
import { type Href, Redirect, router, useLocalSearchParams } from "expo-router";
import { useMemo, useRef, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";

import {
  AppButton,
  AppCard,
  ConfirmationDialog,
  InlineAlert,
  LabeledInput,
  RetryState,
  ScreenShell,
  SkeletonBlock,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import { OCRAnalysisChoices } from "@/components/ocr-analysis-choices";
import { ApiError } from "@/lib/api";
import {
  createAnalysisIdempotencyKey,
  startAnalysis,
} from "@/lib/analysis-client";
import {
  changedOCRFields,
  confidenceLabel,
  confirmOCR,
  createOCRIdempotencyKey,
  fetchOrRunOCR,
  initialOCRFields,
  REQUIRED_OCR_FIELD_NAMES,
  type OCRConfirmedFields,
  type OCRFieldName,
  type OCRReviewData,
  validateOCRConfirmation,
} from "@/lib/ocr-client";
import { fetchPrivateThumbnail } from "@/lib/receipt-client";
import { useAuth } from "@/state/auth-context";
import { useIsOnline } from "@/state/network-context";
import { palette, radius, spacing } from "@/theme/tokens";

const FIELD_ORDER: {
  name: OCRFieldName;
  label: string;
  keyboard?: "default" | "decimal-pad" | "phone-pad";
}[] = [
  { name: "provider_code", label: "Provider" },
  { name: "transaction_reference", label: "Transaction reference" },
  { name: "amount", label: "Amount", keyboard: "decimal-pad" },
  { name: "currency", label: "Currency" },
  { name: "sender_name", label: "Sender name" },
  { name: "sender_phone", label: "Sender phone", keyboard: "phone-pad" },
  { name: "receiver_name", label: "Receiver name" },
  { name: "receiver_phone", label: "Receiver phone", keyboard: "phone-pad" },
  { name: "occurred_at", label: "Date and time" },
  { name: "status_text", label: "Receipt status" },
];

const REQUIRED_FIELD_ORDER = FIELD_ORDER.filter(({ name }) =>
  REQUIRED_OCR_FIELD_NAMES.includes(name),
);
const OPTIONAL_FIELD_ORDER = FIELD_ORDER.filter(
  ({ name }) => !REQUIRED_OCR_FIELD_NAMES.includes(name),
);

function readableError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error
    ? error.message
    : "The OCR review could not be loaded. Please retry.";
}

function warningMessage(code: string): string {
  const labels: Record<string, string> = {
    OCR_ENGINE_UNAVAILABLE:
      "Automatic text reading is unavailable. Inspect the private image and retry if needed; any saved risk result will state this limitation.",
    OCR_ENGINE_TIMEOUT:
      "Automatic text reading took too long. Retry if needed; any saved risk result will state this limitation.",
    OCR_ENGINE_FAILED:
      "Automatic text reading could not finish. The original private image is unchanged.",
    CRITICAL_OCR_FIELDS_MISSING:
      "Some transaction details were not detected. They are required only if you choose reference comparison.",
    UNKNOWN_TEMPLATE_GENERIC_FALLBACK:
      "This layout is not recognised, so a generic parser was used.",
  };
  return (
    labels[code] ?? "Review this note and the private image before acting."
  );
}

function originalField(review: OCRReviewData, name: OCRFieldName) {
  if (name === "provider_code") {
    return {
      value: review.provider.value,
      valid: Boolean(review.provider.value),
      requires_review: review.provider.requires_review,
      confidence: review.provider.confidence,
      raw_value: review.provider.value,
      source_token_ids: [],
      warnings: review.provider.warnings,
    };
  }
  return review.fields[name];
}

export default function OCRReviewScreen() {
  const { transactionId } = useLocalSearchParams<{ transactionId: string }>();
  const { request, response, status } = useAuth();
  const online = useIsOnline();
  const { width } = useWindowDimensions();
  const validId = typeof transactionId === "string" && transactionId.length > 0;
  const runKey = useRef(createOCRIdempotencyKey("run"));
  const confirmationKey = useRef(createOCRIdempotencyKey("confirm"));
  const screenshotAnalysisKey = useRef(createAnalysisIdempotencyKey());
  const referenceAnalysisKey = useRef(createAnalysisIdempotencyKey());
  const [fields, setFields] = useState<OCRConfirmedFields | null>(null);
  const [errors, setErrors] = useState<Partial<Record<OCRFieldName, string>>>(
    {},
  );
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [zoomVisible, setZoomVisible] = useState(false);
  const [comparisonVisible, setComparisonVisible] = useState(false);
  const [rawTextVisible, setRawTextVisible] = useState(false);

  const review = useQuery({
    queryKey: ["ocr-review", transactionId],
    queryFn: () => fetchOrRunOCR(request, transactionId ?? "", runKey.current),
    enabled: validId && status === "authenticated" && online,
    retry: 1,
    staleTime: 0,
  });
  const preview = useQuery({
    queryKey: ["private-receipt", transactionId, "ocr-review"],
    queryFn: () => fetchPrivateThumbnail(response, transactionId ?? ""),
    enabled: validId && status === "authenticated" && online,
    staleTime: 0,
    gcTime: 0,
    retry: 1,
  });

  const activeFields = review.data
    ? (fields ?? initialOCRFields(review.data))
    : null;

  const changed = useMemo(
    () =>
      review.data && activeFields
        ? changedOCRFields(review.data, activeFields)
        : [],
    [activeFields, review.data],
  );
  const confirmation = useMutation({
    mutationFn: () => {
      if (!review.data || !activeFields)
        throw new Error("OCR review is not ready.");
      return confirmOCR(
        request,
        transactionId ?? "",
        review.data,
        activeFields,
        confirmationKey.current,
      );
    },
    onSuccess: () => setConfirmVisible(false),
    onError: (error) => {
      setConfirmVisible(false);
      if (!(error instanceof ApiError) || !error.fieldErrors) return;
      setErrors(
        Object.fromEntries(
          Object.entries(error.fieldErrors).map(([name, messages]) => [
            name,
            messages[0],
          ]),
        ),
      );
    },
  });
  const openAnalysis = (analysisRunId: string) =>
    router.replace({
      pathname: "/analysis/[analysisRunId]",
      params: { analysisRunId },
    } as unknown as Href);
  const screenshotAnalysis = useMutation({
    mutationFn: () => {
      if (!review.data) throw new Error("OCR review is not ready.");
      return startAnalysis(
        request,
        transactionId ?? "",
        screenshotAnalysisKey.current,
        {
          mode: "screenshot_only",
          ocrResultId: review.data.ocr_result_id,
        },
      );
    },
    onSuccess: (started) => openAnalysis(started.analysis_run_id),
  });
  const referenceAnalysis = useMutation({
    mutationFn: () => {
      if (!confirmation.data)
        throw new Error(
          "Confirm the receipt details before checking a reference.",
        );
      return startAnalysis(
        request,
        transactionId ?? "",
        referenceAnalysisKey.current,
      );
    },
    onSuccess: (started) => openAnalysis(started.analysis_run_id),
  });

  const requestConfirmation = () => {
    if (!review.data || !activeFields) return;
    const nextErrors = validateOCRConfirmation(activeFields);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length === 0) setConfirmVisible(true);
  };

  if (status === "restoring") {
    return (
      <ScreenShell title="Review screenshot risk">
        <SkeletonBlock label="Restoring secure session" />
      </ScreenShell>
    );
  }
  if (status !== "authenticated") return <Redirect href="/(auth)/login" />;

  const receiptPanel = (
    <AppCard>
      <View style={uiStyles.row}>
        <Text style={uiStyles.cardTitle}>Private receipt</Text>
        <StatusBadge label="Owner only" tone="success" />
      </View>
      {preview.isPending ? (
        <SkeletonBlock label="Loading private receipt" />
      ) : preview.isError ? (
        <RetryState
          message={readableError(preview.error)}
          onRetry={() => void preview.refetch()}
        />
      ) : (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Open zoomable receipt"
          accessibilityHint="Opens the private receipt in a zoomable view"
          onPress={() => setZoomVisible(true)}
        >
          <Image
            source={{ uri: preview.data }}
            accessibilityLabel="Private receipt for OCR review"
            style={[
              styles.preview,
              {
                height:
                  width >= 820 ? 560 : Math.min(520, Math.max(360, width)),
              },
            ]}
            contentFit="contain"
          />
          <Text style={styles.zoomHint}>Tap to inspect and zoom</Text>
        </Pressable>
      )}
      <InlineAlert
        tone="info"
        title="Private image evidence"
        message="Automatic reading can make mistakes. Inspect the image before using any extracted value for the optional transaction comparison."
      />
    </AppCard>
  );

  const enteredFields = review.data
    ? changed.filter((name) => !originalField(review.data!, name)?.value)
    : [];
  const correctedFields = changed.filter(
    (name) => !enteredFields.includes(name),
  );
  const errorEntries = FIELD_ORDER.flatMap(({ name, label }) =>
    errors[name] ? [`${label}: ${errors[name]}`] : [],
  );
  const editSummary = changed.length
    ? `${enteredFields.length} entered, ${correctedFields.length} corrected`
    : "No edits";

  const renderField = (
    { name, label, keyboard }: (typeof FIELD_ORDER)[number],
    required: boolean,
  ) => {
    if (!review.data || !activeFields) return null;
    const source = originalField(review.data, name);
    const hint = source?.value
      ? confidenceLabel(source)
      : required
        ? "Not detected — enter only the value shown in the image"
        : "Optional — leave blank when it is not shown";
    return (
      <View key={name} style={styles.fieldGroup}>
        <LabeledInput
          label={`${label}${required ? " (required)" : " (optional)"}`}
          value={activeFields[name]}
          keyboardType={keyboard}
          onChangeText={(value) => {
            setFields((current) => ({
              ...(current ?? initialOCRFields(review.data!)),
              [name]: value,
            }));
            setErrors((current) => ({
              ...current,
              [name]: undefined,
            }));
            confirmation.reset();
            referenceAnalysis.reset();
          }}
          error={errors[name]}
          hint={hint}
        />
        {source?.raw_value && source.raw_value !== activeFields[name] ? (
          <Text selectable style={styles.originalValue}>
            OCR read: {source.raw_value}
          </Text>
        ) : null}
      </View>
    );
  };

  return (
    <ScreenShell
      title="Review screenshot risk"
      subtitle="Text and image evidence estimate fraud risk. Comparing transaction details is optional and is not live mobile-network verification."
    >
      {!validId ? (
        <InlineAlert
          tone="error"
          title="Receipt unavailable"
          message="The receipt link is invalid. Return to uploads and try again."
        />
      ) : !online ? (
        <AppCard>
          <Text style={uiStyles.cardTitle}>Review paused</Text>
          <Text style={uiStyles.muted}>
            Reconnect to load the private receipt and OCR evidence.
          </Text>
        </AppCard>
      ) : review.isPending ? (
        <AppCard>
          <SkeletonBlock label="Reading receipt text" />
          <Text selectable style={uiStyles.muted}>
            Creating protected image variants and reading visible text…
          </Text>
        </AppCard>
      ) : review.isError ? (
        <RetryState
          message={readableError(review.error)}
          onRetry={() => void review.refetch()}
        />
      ) : review.data && activeFields ? (
        <>
          {review.data.status === "OCR_PARTIAL" ? (
            <InlineAlert
              tone="warning"
              title="Automatic reading is partial"
              message="Some visible text could not be read. You can still save the screenshot-risk result, or open the optional transaction comparison and enter only values shown in the image."
            />
          ) : (
            <StatusBadge label="Ready for your review" tone="success" />
          )}
          {review.data.warnings.map((warning) => (
            <InlineAlert
              key={warning}
              tone="warning"
              title="Review note"
              message={warningMessage(warning)}
            />
          ))}
          <OCRAnalysisChoices
            preview={review.data.fraud_preview}
            online={online}
            saving={screenshotAnalysis.isPending}
            saveError={
              screenshotAnalysis.isError
                ? readableError(screenshotAnalysis.error)
                : null
            }
            comparisonExpanded={comparisonVisible}
            onSave={() => screenshotAnalysis.mutate()}
            onToggleComparison={() => {
              setComparisonVisible((current) => !current);
              screenshotAnalysis.reset();
            }}
          />
          <View
            style={[
              styles.reviewLayout,
              comparisonVisible && width >= 820
                ? styles.reviewLayoutWide
                : null,
            ]}
          >
            <View
              style={[
                styles.panel,
                !comparisonVisible && width >= 820
                  ? styles.receiptPanelSolo
                  : null,
              ]}
            >
              {receiptPanel}
            </View>
            {comparisonVisible ? (
              <View style={styles.panel}>
                <AppCard>
                  <View style={uiStyles.row}>
                    <Text style={uiStyles.cardTitle}>
                      Optional transaction comparison
                    </Text>
                    <StatusBadge
                      label={editSummary}
                      tone={changed.length ? "warning" : "info"}
                    />
                  </View>
                  <InlineAlert
                    tone="info"
                    title="Use only values visible in the image"
                    message="Do not guess or invent missing details. The required fields below apply only to stored/imported reference comparison; optional sender and receiver fields can stay blank."
                  />
                  {errorEntries.length ? (
                    <InlineAlert
                      tone="error"
                      title={`Fix ${errorEntries.length} highlighted field${errorEntries.length === 1 ? "" : "s"}`}
                      message={errorEntries.join("\n")}
                    />
                  ) : null}
                  <View style={styles.formSection}>
                    <Text style={styles.sectionTitle}>
                      Required only for comparison
                    </Text>
                    <Text style={uiStyles.muted}>
                      These values are needed to compare the screenshot with a
                      stored or imported transaction record.
                    </Text>
                    {REQUIRED_FIELD_ORDER.map((field) =>
                      renderField(field, true),
                    )}
                  </View>
                  <View style={styles.formSection}>
                    <Text style={styles.sectionTitle}>Additional details</Text>
                    <Text style={uiStyles.muted}>
                      Leave any value blank when it is not visible in the image.
                    </Text>
                    {OPTIONAL_FIELD_ORDER.map((field) =>
                      renderField(field, false),
                    )}
                  </View>
                  {confirmation.isError ? (
                    <InlineAlert
                      tone="error"
                      title="Confirmation not saved"
                      message={readableError(confirmation.error)}
                    />
                  ) : null}
                  <AppButton
                    label="Save details for reference comparison"
                    onPress={requestConfirmation}
                    loading={confirmation.isPending}
                    disabled={!online}
                  />
                </AppCard>
              </View>
            ) : null}
          </View>
          {review.data.raw_text ? (
            <AppCard>
              <Text style={uiStyles.cardTitle}>Technical OCR text</Text>
              <Text style={uiStyles.muted}>
                Optional technical evidence. The risk result above already uses
                the stored OCR assessment.
              </Text>
              <AppButton
                label={
                  rawTextVisible ? "Hide raw OCR text" : "Show raw OCR text"
                }
                onPress={() => setRawTextVisible((current) => !current)}
                variant="secondary"
                accessibilityState={{ expanded: rawTextVisible }}
                accessibilityHint="Shows or hides the raw text read from the private image"
              />
              {rawTextVisible ? (
                <>
                  <Text selectable style={styles.rawText}>
                    {review.data.raw_text}
                  </Text>
                  <Text style={uiStyles.muted}>
                    Pipeline {review.data.pipeline_version} · selected{" "}
                    {review.data.selected_variant}. Raw token boxes remain
                    protected as technical evidence.
                  </Text>
                </>
              ) : null}
            </AppCard>
          ) : null}
        </>
      ) : null}

      {confirmation.isSuccess ? (
        <AppCard>
          <StatusBadge label="Details confirmed" tone="success" />
          <Text style={uiStyles.cardTitle}>OCR review complete</Text>
          <Text selectable style={uiStyles.body}>
            Your confirmed snapshot is saved separately from the original OCR
            result. You can now compare it with stored/imported reference data.
          </Text>
          <InlineAlert
            tone="info"
            title="Verification is not live provider confirmation"
            message="This check uses reference records imported by an administrator. It does not query a mobile-network operator."
          />
          {referenceAnalysis.isError ? (
            <InlineAlert
              tone="error"
              title="Reference check unavailable"
              message={readableError(referenceAnalysis.error)}
            />
          ) : null}
          <AppButton
            label="Check stored/imported reference"
            onPress={() => referenceAnalysis.mutate()}
            loading={referenceAnalysis.isPending}
            disabled={!online}
          />
        </AppCard>
      ) : null}
      <AppButton
        label="Back"
        onPress={() => router.back()}
        variant="secondary"
      />

      <ConfirmationDialog
        visible={confirmVisible}
        title="Confirm these receipt details?"
        message={`This saves an immutable reviewed snapshot. ${enteredFields.length} manual entr${enteredFields.length === 1 ? "y" : "ies"} and ${correctedFields.length} correction${correctedFields.length === 1 ? "" : "s"} will be documented automatically. Check the private image first.`}
        confirmLabel="Save reviewed details"
        onConfirm={() => confirmation.mutate()}
        onCancel={() => setConfirmVisible(false)}
      />
      <Modal
        visible={zoomVisible}
        animationType="slide"
        onRequestClose={() => setZoomVisible(false)}
      >
        <View style={styles.zoomScreen} accessibilityViewIsModal>
          <ScrollView
            contentInsetAdjustmentBehavior="automatic"
            minimumZoomScale={1}
            maximumZoomScale={4}
            contentContainerStyle={styles.zoomContent}
          >
            <Image
              source={preview.data ? { uri: preview.data } : null}
              accessibilityLabel="Zoomable private receipt"
              style={styles.zoomImage}
              contentFit="contain"
            />
          </ScrollView>
          <View style={styles.zoomActions}>
            <AppButton
              label="Close receipt"
              onPress={() => setZoomVisible(false)}
              variant="secondary"
            />
          </View>
        </View>
      </Modal>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  reviewLayout: { gap: spacing.md },
  reviewLayoutWide: { flexDirection: "row", alignItems: "flex-start" },
  panel: { flex: 1, minWidth: 0 },
  receiptPanelSolo: { width: "100%", maxWidth: 720, alignSelf: "center" },
  formSection: { gap: spacing.md },
  fieldGroup: { gap: spacing.sm },
  sectionTitle: {
    color: palette.ink,
    fontSize: 17,
    lineHeight: 24,
    fontWeight: "800",
  },
  preview: {
    width: "100%",
    borderRadius: radius.md,
    backgroundColor: palette.canvas,
  },
  zoomHint: {
    color: palette.forestDark,
    fontWeight: "700",
    textAlign: "center",
    paddingTop: spacing.sm,
  },
  originalValue: {
    color: palette.muted,
    fontSize: 13,
    backgroundColor: palette.canvas,
    padding: spacing.sm,
    borderRadius: radius.sm,
  },
  rawText: {
    color: palette.ink,
    fontFamily: "monospace",
    lineHeight: 22,
    backgroundColor: palette.canvas,
    padding: spacing.md,
    borderRadius: radius.sm,
  },
  zoomScreen: { flex: 1, backgroundColor: palette.ink },
  zoomContent: { flexGrow: 1, alignItems: "center", justifyContent: "center" },
  zoomImage: { width: "100%", minHeight: 700 },
  zoomActions: { padding: spacing.md, backgroundColor: palette.surface },
});

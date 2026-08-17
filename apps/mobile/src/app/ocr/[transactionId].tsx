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
import { TextFraudRiskCard } from "@/components/text-fraud-risk-card";
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

function readableError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error
    ? error.message
    : "The OCR review could not be loaded. Please retry.";
}

function warningMessage(code: string): string {
  const labels: Record<string, string> = {
    OCR_ENGINE_UNAVAILABLE:
      "Automatic text reading is unavailable. Enter the receipt details manually.",
    OCR_ENGINE_TIMEOUT:
      "Automatic text reading took too long. Check and enter missing details manually.",
    OCR_ENGINE_FAILED:
      "Automatic text reading could not finish. Your original receipt is still safe.",
    CRITICAL_OCR_FIELDS_MISSING:
      "Some required details were not detected and need your review.",
    UNKNOWN_TEMPLATE_GENERIC_FALLBACK:
      "This layout is not recognised, so a generic parser was used.",
  };
  return labels[code] ?? "Check the receipt carefully before confirming.";
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
  const analysisKey = useRef(createAnalysisIdempotencyKey());
  const [fields, setFields] = useState<OCRConfirmedFields | null>(null);
  const [reasons, setReasons] = useState<Partial<Record<OCRFieldName, string>>>(
    {},
  );
  const [errors, setErrors] = useState<Partial<Record<OCRFieldName, string>>>(
    {},
  );
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [zoomVisible, setZoomVisible] = useState(false);

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
        reasons,
        confirmationKey.current,
      );
    },
    onSuccess: () => setConfirmVisible(false),
  });
  const analysis = useMutation({
    mutationFn: () => {
      if (!confirmation.data)
        throw new Error(
          "Confirm the receipt details before checking a reference.",
        );
      return startAnalysis(request, transactionId ?? "", analysisKey.current);
    },
    onSuccess: (started) =>
      router.replace({
        pathname: "/analysis/[analysisRunId]",
        params: { analysisRunId: started.analysis_run_id },
      } as unknown as Href),
  });

  const requestConfirmation = () => {
    if (!review.data || !activeFields) return;
    const nextErrors = validateOCRConfirmation(
      review.data,
      activeFields,
      reasons,
    );
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length === 0) setConfirmVisible(true);
  };

  if (status === "restoring") {
    return (
      <ScreenShell title="Review receipt details">
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
            style={styles.preview}
            contentFit="contain"
          />
          <Text style={styles.zoomHint}>Tap to inspect and zoom</Text>
        </Pressable>
      )}
      <InlineAlert
        tone="info"
        title="Check the image"
        message="Automatic reading can make mistakes. Compare every important value with the receipt before confirming."
      />
    </AppCard>
  );

  return (
    <ScreenShell
      title="Review receipt details"
      subtitle="OCR reads visible text; it does not prove authenticity or verify a transaction with a mobile network."
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
            Creating safe image variants and reading visible text…
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
              message="Your receipt is safe, but some details need manual entry before analysis can begin."
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
          <TextFraudRiskCard preview={review.data.fraud_preview} />
          <View
            style={[
              styles.reviewLayout,
              width >= 820 ? styles.reviewLayoutWide : null,
            ]}
          >
            <View style={styles.panel}>{receiptPanel}</View>
            <View style={styles.panel}>
              <AppCard>
                <View style={uiStyles.row}>
                  <Text style={uiStyles.cardTitle}>Extracted details</Text>
                  <StatusBadge
                    label={`${changed.length} correction${changed.length === 1 ? "" : "s"}`}
                    tone={changed.length ? "warning" : "info"}
                  />
                </View>
                {FIELD_ORDER.map(({ name, label, keyboard }) => {
                  const source = originalField(review.data, name);
                  const changedField = changed.includes(name);
                  return (
                    <View key={name} style={{ gap: spacing.sm }}>
                      <LabeledInput
                        label={label}
                        value={activeFields[name]}
                        keyboardType={keyboard}
                        onChangeText={(value) => {
                          setFields((current) => ({
                            ...(current ?? initialOCRFields(review.data)),
                            [name]: value,
                          }));
                          setErrors((current) => ({
                            ...current,
                            [name]: undefined,
                          }));
                          confirmation.reset();
                          analysis.reset();
                        }}
                        error={errors[name]}
                        hint={confidenceLabel(source)}
                      />
                      {source?.raw_value &&
                      source.raw_value !== activeFields[name] ? (
                        <Text selectable style={styles.originalValue}>
                          OCR read: {source.raw_value}
                        </Text>
                      ) : null}
                      {changedField ? (
                        <LabeledInput
                          label={`Reason for changing ${label.toLowerCase()}`}
                          value={reasons[name] ?? ""}
                          onChangeText={(value) => {
                            setReasons((current) => ({
                              ...current,
                              [name]: value,
                            }));
                            setErrors((current) => ({
                              ...current,
                              [name]: undefined,
                            }));
                          }}
                          placeholder="What did you check on the receipt?"
                          multiline
                          error={errors[name]}
                        />
                      ) : null}
                    </View>
                  );
                })}
                {confirmation.isError ? (
                  <InlineAlert
                    tone="error"
                    title="Confirmation not saved"
                    message={readableError(confirmation.error)}
                  />
                ) : null}
                <AppButton
                  label="Confirm reviewed details"
                  onPress={requestConfirmation}
                  loading={confirmation.isPending}
                  disabled={!online}
                />
              </AppCard>
            </View>
          </View>
          {review.data.raw_text ? (
            <AppCard>
              <Text style={uiStyles.cardTitle}>Raw OCR text</Text>
              <Text selectable style={styles.rawText}>
                {review.data.raw_text}
              </Text>
              <Text style={uiStyles.muted}>
                Pipeline {review.data.pipeline_version} · selected{" "}
                {review.data.selected_variant}. Raw token boxes remain protected
                as technical evidence.
              </Text>
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
          {analysis.isError ? (
            <InlineAlert
              tone="error"
              title="Reference check unavailable"
              message={readableError(analysis.error)}
            />
          ) : null}
          <AppButton
            label="Check stored/imported reference"
            onPress={() => analysis.mutate()}
            loading={analysis.isPending}
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
        message={`This saves an immutable reviewed snapshot and ${changed.length} documented correction${changed.length === 1 ? "" : "s"}. Check the private image first.`}
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
  preview: {
    width: "100%",
    aspectRatio: 0.75,
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

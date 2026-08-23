import { useMutation } from "@tanstack/react-query";
import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import { type Href, router } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import {
  AppButton,
  AppCard,
  ConfirmationDialog,
  InlineAlert,
  ScreenShell,
  StatusBadge,
  uiStyles,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  prepareReceipt,
  type ReceiptSource,
  type ReceiptUploadData,
  type SelectedReceipt,
  uploadReceipt,
} from "@/lib/receipt-client";
import { uploadQualityMessages } from "@/lib/upload-quality";
import { useAuth } from "@/state/auth-context";
import { useIsOnline } from "@/state/network-context";
import { palette, radius } from "@/theme/tokens";

function readableError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error
    ? error.message
    : "The screenshot could not be secured. Please retry.";
}

export default function UploadScreen() {
  const { request } = useAuth();
  const online = useIsOnline();
  const [selected, setSelected] = useState<SelectedReceipt | null>(null);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [removeVisible, setRemoveVisible] = useState(false);
  const [uploaded, setUploaded] = useState<ReceiptUploadData | null>(null);

  const upload = useMutation({
    mutationFn: (receipt: SelectedReceipt) => uploadReceipt(request, receipt),
    onSuccess: setUploaded,
  });

  const acceptAsset = (
    result: ImagePicker.ImagePickerResult,
    source: ReceiptSource,
  ) => {
    if (result.canceled || !result.assets[0]) return;
    try {
      setSelected(prepareReceipt(result.assets[0], source));
      setSelectionError(null);
      setPermissionError(null);
      setUploaded(null);
      upload.reset();
    } catch (error) {
      setSelectionError(readableError(error));
    }
  };

  const chooseCamera = async () => {
    setPermissionError(null);
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      setPermissionError(
        "Camera access is denied. Enable it in device settings, or choose a screenshot from your gallery.",
      );
      return;
    }
    acceptAsset(
      await ImagePicker.launchCameraAsync({
        mediaTypes: ["images"],
        allowsEditing: false,
      }),
      "CAMERA",
    );
  };

  const chooseGallery = async () => {
    setPermissionError(null);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setPermissionError(
        "Photo access is denied. Enable it in device settings, or use the camera.",
      );
      return;
    }
    acceptAsset(
      await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsEditing: false,
        allowsMultipleSelection: false,
      }),
      "GALLERY",
    );
  };

  const clearSelection = () => {
    setSelected(null);
    setUploaded(null);
    setSelectionError(null);
    upload.reset();
    setRemoveVisible(false);
  };
  const uploadWarnings = uploaded
    ? uploadQualityMessages(uploaded.receipt.quality.warnings, {
        exactMatchFound: uploaded.receipt.duplicate_warning.exact_match_found,
        nearMatchFound: uploaded.receipt.duplicate_warning.near_match_found,
      })
    : [];

  return (
    <ScreenShell
      title="Secure a screenshot"
      subtitle="Take a clear photo or choose an existing JPEG, PNG, or WebP image. Originals stay private."
    >
      <InlineAlert
        tone="info"
        title="Before you submit"
        message="Maximum 10 MB. Keep the full message visible, avoid glare, and make the text readable. Quality warnings are not fraud decisions."
      />

      {permissionError ? (
        <InlineAlert
          tone="warning"
          title="Permission needed"
          message={permissionError}
        />
      ) : null}
      {selectionError ? (
        <InlineAlert
          tone="error"
          title="Choose another image"
          message={selectionError}
        />
      ) : null}

      {!selected ? (
        <AppCard>
          <Text style={uiStyles.cardTitle}>Add your screenshot</Text>
          <Text style={uiStyles.muted}>
            Only the screenshot you select is sent. MoMo-FDVS does not browse
            your gallery or claim live mobile-network verification.
          </Text>
          <AppButton
            label="Take screenshot photo"
            onPress={() => void chooseCamera()}
          />
          <AppButton
            label="Choose from gallery"
            onPress={() => void chooseGallery()}
            variant="secondary"
          />
        </AppCard>
      ) : (
        <AppCard>
          <View style={uiStyles.row}>
            <Text style={uiStyles.cardTitle}>Screenshot preview</Text>
            <StatusBadge
              label={selected.source === "CAMERA" ? "Camera" : "Gallery"}
            />
          </View>
          <Image
            source={{ uri: selected.asset.uri }}
            accessibilityLabel="Selected screenshot preview"
            style={styles.preview}
            contentFit="contain"
          />
          <Text style={uiStyles.muted} numberOfLines={2}>
            {selected.filename} · {selected.asset.width} ×{" "}
            {selected.asset.height}
          </Text>
          <View style={uiStyles.row}>
            <AppButton
              label="Replace with camera"
              onPress={() => void chooseCamera()}
              variant="secondary"
            />
            <AppButton
              label="Replace from gallery"
              onPress={() => void chooseGallery()}
              variant="secondary"
            />
          </View>
          <AppButton
            label="Remove selection"
            onPress={() => setRemoveVisible(true)}
            variant="danger"
          />
        </AppCard>
      )}

      {upload.isPending ? (
        <InlineAlert
          tone="info"
          title="Securing screenshot"
          message="Validating the image, creating its evidence hashes, and saving it privately. Keep this screen open."
        />
      ) : null}
      {upload.isError ? (
        <AppCard>
          <InlineAlert
            tone="error"
            title="Upload not completed"
            message={readableError(upload.error)}
          />
          <AppButton
            label="Retry secure upload"
            onPress={() => selected && upload.mutate(selected)}
            disabled={!online || !selected}
            variant="secondary"
          />
        </AppCard>
      ) : null}

      {uploaded ? (
        <AppCard>
          <StatusBadge label="Uploaded securely" tone="success" />
          <Text style={uiStyles.cardTitle}>Private screenshot saved</Text>
          <Text style={uiStyles.body}>
            The original is immutable evidence. The next step is OCR review; no
            fraud result has been produced yet.
          </Text>
          {uploadWarnings.length > 0 ? (
            <InlineAlert
              tone="warning"
              title="Image review notes"
              message={uploadWarnings
                .map((message) => `• ${message}`)
                .join("\n")}
            />
          ) : null}
          <AppButton
            label="Review screenshot"
            onPress={() =>
              router.push({
                pathname: "/ocr/[transactionId]",
                params: { transactionId: uploaded.transaction.id },
              } as unknown as Href)
            }
          />
          <AppButton
            label="Secure another screenshot"
            onPress={clearSelection}
            variant="secondary"
          />
        </AppCard>
      ) : selected ? (
        <AppButton
          label="Securely upload screenshot"
          onPress={() => upload.mutate(selected)}
          loading={upload.isPending}
          disabled={!online}
        />
      ) : null}

      <ConfirmationDialog
        visible={removeVisible}
        title="Remove this selection?"
        message="The local selection will be cleared. A screenshot already uploaded as evidence is not deleted."
        confirmLabel="Remove selection"
        destructive
        onConfirm={clearSelection}
        onCancel={() => setRemoveVisible(false)}
      />
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  preview: {
    width: "100%",
    aspectRatio: 0.75,
    borderRadius: radius.md,
    backgroundColor: palette.canvas,
    borderWidth: 1,
    borderColor: palette.border,
  },
});

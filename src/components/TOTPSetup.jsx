import React, { useState, useEffect } from "react";
import {
  Smartphone,
  QrCode,
  Copy,
  Download,
  CheckCircle,
  AlertCircle,
  ArrowLeft,
  Eye,
  EyeOff,
} from "lucide-react";

const TOTPSetup = ({ onComplete, onBack }) => {
  const [step, setStep] = useState(1); // 1: Instructions, 2: QR Code, 3: Verification, 4: Backup Codes
  const [totpData, setTotpData] = useState(null);
  const [verificationCode, setVerificationCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [disabled, setDisabled] = useState(false);

  // Step 1: Generate TOTP secret and QR code
  const setupTOTP = async () => {
    setLoading(true);
    setError("");

    try {
      // Check if this is first-time setup (use temp_token) or regular setup (use token)
      const isFirstTimeSetup = localStorage.getItem("setup_username");
      const authToken = isFirstTimeSetup
        ? localStorage.getItem("temp_token")
        : localStorage.getItem("token");

      const response = await fetch("/api/auth/totp/setup", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${authToken}`,
          "Content-Type": "application/json",
        },
      });
console.log("object",response)
      console.log("object1",response.status)
      if (response.status === 403) {
        setDisabled(true);
        setError("Two-factor authentication is disabled by administrator.");
        return;
      }

      const data = await response.json();

      if (data.success) {
        setTotpData(data);
        setStep(2);
      } else {
        setError(data.error || "Error during TOTP setup");
      }
    } catch (err) {
      setError("Connection error");
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Verify TOTP code
  const verifyCode = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      setError("Please enter a 6-digit code");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Check if this is first-time setup (use temp_token) or regular setup (use token)
      const isFirstTimeSetup = localStorage.getItem("setup_username");
      const authToken = isFirstTimeSetup
        ? localStorage.getItem("temp_token")
        : localStorage.getItem("token");

      const response = await fetch("/api/auth/totp/verify", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${authToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ code: verificationCode }),
      });

      const data = await response.json();

      if (data.success) {
        setStep(4);
      } else {
        setError(data.error || "Invalid code");
      }
    } catch (err) {
      setError("Connection error");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error("Error copying:", err);
    }
  };

  const downloadBackupCodes = () => {
    if (!totpData?.backup_codes) return;

    const content = `2FA BACKUP CODES - Photo Validator

IMPORTANT: Keep these codes in a safe place. Each code can only be used once.

${totpData.backup_codes.map((code, i) => `${i + 1}. ${code}`).join("\n")}

Generated on: ${new Date().toLocaleDateString(
      "en-US"
    )} at ${new Date().toLocaleTimeString("en-US")}`;

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "photo-validator-backup-codes.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Start configuration automatically
  useEffect(() => {
    if (step === 1) {
      setupTOTP();
    }
  }, []);

  if (disabled) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white p-6 rounded-lg shadow text-center">
          <AlertCircle className="mx-auto h-10 w-10 text-red-500 mb-4" />
          <p className="text-gray-700 mb-6">
            Two-factor authentication is currently disabled for your account.
          </p>
          <button
            onClick={onBack}
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            Go back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-lg w-full space-y-8">
        {/* Header with back button */}
        <div className="text-center">
          <div className="flex items-center justify-between mb-6">
            <button
              onClick={onBack}
              className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="h-5 w-5 mr-1" />
              Back
            </button>
            <div className="text-sm font-medium text-gray-500">
              {step === 1 && "Configuration..."}
              {step === 2 && "Step 1/3"}
              {step === 3 && "Step 2/3"}
              {step === 4 && "Done!"}
            </div>
          </div>

          <Smartphone className="mx-auto h-16 w-16 text-indigo-600" />
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Authenticator Configuration
          </h2>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <AlertCircle className="h-5 w-5 text-red-400 mr-2 flex-shrink-0" />
              <div className="text-sm text-red-700">{error}</div>
            </div>
          </div>
        )}

        {/* Step 1: Loading */}
        {step === 1 && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">
              Setting up authentication...
            </p>
          </div>
        )}

        {/* Step 2: QR Code */}
        {step === 2 && totpData && (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Scan the QR code
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                Use your authenticator app (Google Authenticator,
                Microsoft Authenticator, etc.)
              </p>
            </div>

            {/* QR Code */}
            <div className="flex justify-center p-6 bg-white rounded-lg border-2 border-dashed border-gray-300">
              <img
                src={`data:image/png;base64,${totpData.qr_code}`}
                alt="QR Code TOTP"
                className="w-48 h-48"
              />
            </div>

            {/* Manual entry option */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-900 mb-2">
                Manual Entry (if QR code doesn't work)
              </h4>
              <div className="flex items-center space-x-2">
                <input
                  type={showSecret ? "text" : "password"}
                  value={totpData.secret}
                  readOnly
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm font-mono bg-white"
                />
                <button
                  onClick={() => setShowSecret(!showSecret)}
                  className="p-2 text-gray-600 hover:text-gray-900"
                >
                  {showSecret ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
                <button
                  onClick={() => copyToClipboard(totpData.secret)}
                  className="p-2 text-gray-600 hover:text-gray-900"
                >
                  <Copy className="h-4 w-4" />
                </button>
              </div>
            </div>

            <button
              onClick={() => setStep(3)}
              className="w-full py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
            >
              I have configured the app
            </button>
          </div>
        )}

        {/* Step 3: Verification */}
        {step === 3 && (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Verify your configuration
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                Enter the 6-digit code displayed in your authenticator
                app
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Verification Code
                </label>
                <input
                  type="text"
                  placeholder="000000"
                  maxLength="6"
                  value={verificationCode}
                  onChange={(e) =>
                    setVerificationCode(e.target.value.replace(/\D/g, ""))
                  }
                  className="w-full px-4 py-3 border border-gray-300 rounded-md text-center text-2xl font-mono tracking-wider focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>

              <button
                onClick={verifyCode}
                disabled={loading || verificationCode.length !== 6}
                className="w-full py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "Verifying..." : "Verify and activate"}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Backup codes */}
        {step === 4 && totpData && (
          <div className="space-y-6">
            <div className="text-center">
              <CheckCircle className="mx-auto h-16 w-16 text-green-500 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Authentication configured!
              </h3>
              <p className="text-sm text-gray-600">
                Here are your backup codes. Keep them in a safe place.
              </p>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex">
                <AlertCircle className="h-5 w-5 text-yellow-400 mr-2 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-700">
                  <strong>Important:</strong> Each code can only be used
                  once. Keep them in a safe place, separate from your phone.
                </div>
              </div>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-900 mb-3">
                Backup Codes
              </h4>
              <div className="grid grid-cols-2 gap-2 text-sm font-mono">
                {totpData.backup_codes.map((code, index) => (
                  <div
                    key={index}
                    className="p-2 bg-gray-50 rounded text-center"
                  >
                    {code}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={downloadBackupCodes}
                className="flex-1 flex items-center justify-center py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
              >
                <Download className="h-4 w-4 mr-2" />
                Download
              </button>
              <button
                onClick={() =>
                  copyToClipboard(totpData.backup_codes.join("\n"))
                }
                className="flex-1 flex items-center justify-center py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
              >
                <Copy className="h-4 w-4 mr-2" />
                Copy
              </button>
            </div>

            <button
              onClick={onComplete}
              className="w-full py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
            >
              Complete setup
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TOTPSetup;

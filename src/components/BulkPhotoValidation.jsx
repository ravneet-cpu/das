import React, { useEffect, useMemo, useState } from "react";
import {
  CheckSquare,
  RefreshCw,
  ThumbsDown,
  ThumbsUp,
  CalendarClock,
  Camera,
  AlertTriangle,
} from "lucide-react";

const CLASSIFICATIONS = [
  "MAIN_HR",
  "MAIN_LR",
  "FRONT",
  "FRONTRIGHT",
  "LEFT",
  "BACK",
  "BACKFRAME",
  "FRAME",
  "SIGN",
  "DET1",
  "DET2",
  "SCALE",
  "INSITU",
  "OTHERS",
];

const BulkPhotoValidation = () => {
  const [photos, setPhotos] = useState([]);
  const [qualityMap, setQualityMap] = useState({});
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");

  const [classification, setClassification] = useState("");
  const [generatePerspective, setGeneratePerspective] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [scheduledDate, setScheduledDate] = useState("");

  const perPage = 30;

  const tokenHeaders = useMemo(
    () => ({
      Authorization: `Bearer ${localStorage.getItem("token")}`,
    }),
    [],
  );

  const filteredPhotos = useMemo(() => {
    if (!search.trim()) return photos;
    const q = search.trim().toLowerCase();
    return photos.filter((p) => p.filename?.toLowerCase().includes(q));
  }, [photos, search]);

  const fetchPhotos = async (targetPage = 1) => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `/api/photos/list?status=pending&page=${targetPage}&limit=${perPage}`,
        { headers: tokenHeaders },
      );
      if (!response.ok) {
        throw new Error(`Failed to load pending photos (${response.status})`);
      }

      const data = await response.json();
      setPhotos(data.photos || []);
      setTotalPages(data.total_pages || 1);
      setTotal(data.total || 0);
      setPage(targetPage);
      setSelected(new Set());
    } catch (err) {
      setError(err.message || "Failed to load pending photos");
    } finally {
      setLoading(false);
    }
  };

  const fetchBatchQuality = async () => {
    try {
      setAnalyzing(true);
      const response = await fetch("/api/photos/batch-analyze-quality", {
        method: "POST",
        headers: {
          ...tokenHeaders,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ folder: "a-valider" }),
      });
      if (!response.ok) return;
      const data = await response.json();
      const nextMap = {};
      (data.results || []).forEach((item) => {
        if (item?.filename) {
          nextMap[item.filename] = item.quality_analysis || null;
        }
      });
      setQualityMap(nextMap);
    } catch {
      // Keep table usable even if quality analysis fails.
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    fetchPhotos(1);
    fetchBatchQuality();
  }, []);

  const toggleSelection = (photoId) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(photoId)) next.delete(photoId);
      else next.add(photoId);
      return next;
    });
  };

  const toggleSelectAllVisible = () => {
    const visibleIds = filteredPhotos.map((p) => p.id);
    const allVisibleSelected =
      visibleIds.length > 0 && visibleIds.every((id) => selected.has(id));

    setSelected((prev) => {
      const next = new Set(prev);
      if (allVisibleSelected) {
        visibleIds.forEach((id) => next.delete(id));
      } else {
        visibleIds.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  const formatBytes = (bytes) => {
    if (!Number.isFinite(bytes)) return "-";
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    const kb = bytes / 1024;
    return `${kb.toFixed(1)} KB`;
  };

  const getQualityBadge = (quality) => {
    if (!quality) return <span className="text-xs text-gray-500">N/A</span>;
    const color = quality.color_code || "gray";
    const cls =
      color === "green"
        ? "bg-green-100 text-green-700"
        : color === "lightgreen"
          ? "bg-lime-100 text-lime-700"
          : color === "orange"
            ? "bg-orange-100 text-orange-700"
            : color === "red"
              ? "bg-red-100 text-red-700"
              : "bg-gray-100 text-gray-700";
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${cls}`}>
        {quality.print_quality_a5 || quality.quality_level || "N/A"}
      </span>
    );
  };

  const selectedPhotos = photos.filter((p) => selected.has(p.id));

  const runBulkAction = async (action) => {
    if (selectedPhotos.length === 0) {
      alert("Please select at least one photo.");
      return;
    }

    if ((action === "validate" || action === "schedule") && !classification) {
      alert("Classification is required for validate/schedule.");
      return;
    }

    if (action === "schedule" && !scheduledDate) {
      alert("Please choose a schedule date/time.");
      return;
    }

    if (action === "reject" && !rejectReason.trim()) {
      alert("Please enter reject reason.");
      return;
    }

    setProcessing(true);
    let success = 0;
    let failed = 0;
    let duplicate = 0;

    for (const photo of selectedPhotos) {
      const payload = {
        photoId: photo.id,
        decision: action === "reject" ? "reject" : "validate",
        newFilename: photo.filename,
      };

      if (action === "validate" || action === "schedule") {
        payload.classification = classification;
        payload.generatePerspective = generatePerspective;
      }
      if (action === "reject") {
        payload.rejectReason = rejectReason.trim();
      }
      if (action === "schedule") {
        payload.scheduledDate = new Date(scheduledDate).toISOString();
      }

      try {
        const response = await fetch("/api/photos/validate", {
          method: "POST",
          headers: {
            ...tokenHeaders,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (response.status === 409) {
          duplicate += 1;
          failed += 1;
          continue;
        }

        if (!response.ok) {
          failed += 1;
          continue;
        }

        success += 1;
      } catch {
        failed += 1;
      }
    }

    alert(
      `Bulk ${action} complete.\nSuccess: ${success}\nFailed: ${failed}\nDuplicates: ${duplicate}`,
    );

    setProcessing(false);
    setSelected(new Set());
    await fetchPhotos(page);
    await fetchBatchQuality();
  };

  return (
    <div className="min-h-screen bg-gray-50 py-6 px-4">
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="bg-white border rounded-lg p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Bulk Photo Validation
              </h1>
              <p className="text-sm text-gray-600">
                Validate, reject, or schedule multiple pending photos at once.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => fetchPhotos(page)}
                className="px-3 py-2 rounded bg-gray-100 hover:bg-gray-200 text-sm flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
              <button
                onClick={fetchBatchQuality}
                className="px-3 py-2 rounded bg-blue-100 hover:bg-blue-200 text-sm flex items-center gap-2"
              >
                <Camera className="w-4 h-4" />
                {analyzing ? "Analyzing..." : "Refresh Quality"}
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white border rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search filename..."
              className="md:col-span-2 px-3 py-2 border rounded"
            />
            <select
              value={classification}
              onChange={(e) => setClassification(e.target.value)}
              className="px-3 py-2 border rounded"
            >
              <option value="">Classification (required for validate)</option>
              {CLASSIFICATIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <input
              type="datetime-local"
              value={scheduledDate}
              onChange={(e) => setScheduledDate(e.target.value)}
              className="px-3 py-2 border rounded"
            />
            <input
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Reject reason"
              className="px-3 py-2 border rounded"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={generatePerspective}
                onChange={(e) => setGeneratePerspective(e.target.checked)}
              />
              Generate perspective (optional)
            </label>

            <button
              onClick={toggleSelectAllVisible}
              className="ml-auto px-3 py-2 rounded bg-gray-100 hover:bg-gray-200 text-sm flex items-center gap-2"
            >
              <CheckSquare className="w-4 h-4" />
              Select all visible
            </button>
            <button
              disabled={processing}
              onClick={() => runBulkAction("validate")}
              className="px-3 py-2 rounded bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white text-sm flex items-center gap-2"
            >
              <ThumbsUp className="w-4 h-4" />
              Validate Selected
            </button>
            <button
              disabled={processing}
              onClick={() => runBulkAction("reject")}
              className="px-3 py-2 rounded bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white text-sm flex items-center gap-2"
            >
              <ThumbsDown className="w-4 h-4" />
              Reject Selected
            </button>
            <button
              disabled={processing}
              onClick={() => runBulkAction("schedule")}
              className="px-3 py-2 rounded bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white text-sm flex items-center gap-2"
            >
              <CalendarClock className="w-4 h-4" />
              Schedule Selected
            </button>
          </div>

          <p className="text-sm text-gray-600">
            Selected: {selected.size} | Page: {page}/{totalPages} | Total
            pending: {total}
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded p-3 text-red-700 text-sm flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {error}
          </div>
        )}

        <div className="bg-white border rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100 text-gray-700">
                <tr>
                  <th className="text-left px-3 py-2">Select</th>
                  <th className="text-left px-3 py-2">Thumbnail</th>
                  <th className="text-left px-3 py-2">Filename</th>
                  <th className="text-left px-3 py-2">Quality</th>
                  <th className="text-left px-3 py-2">Resolution</th>
                  <th className="text-left px-3 py-2">File Size</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="6" className="px-3 py-8 text-center text-gray-500">
                      Loading pending photos...
                    </td>
                  </tr>
                ) : filteredPhotos.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="px-3 py-8 text-center text-gray-500">
                      No photos found.
                    </td>
                  </tr>
                ) : (
                  filteredPhotos.map((photo) => {
                    const quality = qualityMap[photo.filename];
                    const dimensions = quality?.dimensions;
                    return (
                      <tr key={photo.id} className="border-t hover:bg-gray-50">
                        <td className="px-3 py-2">
                          <input
                            type="checkbox"
                            checked={selected.has(photo.id)}
                            onChange={() => toggleSelection(photo.id)}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <a
                            href={`/api/photos/${encodeURIComponent(photo.id)}`}
                            target="_blank"
                            rel="noreferrer"
                            className="block w-16 h-16 border rounded overflow-hidden"
                          >
                            <img
                              src={`/api/photos/${encodeURIComponent(photo.id)}/thumbnail`}
                              alt={photo.filename}
                              className="w-full h-full object-cover"
                            />
                          </a>
                        </td>
                        <td className="px-3 py-2 max-w-[360px] truncate" title={photo.filename}>
                          {photo.filename}
                        </td>
                        <td className="px-3 py-2">{getQualityBadge(quality)}</td>
                        <td className="px-3 py-2">
                          {dimensions
                            ? `${dimensions.width} x ${dimensions.height}`
                            : "-"}
                        </td>
                        <td className="px-3 py-2">
                          {quality?.file_size_mb
                            ? `${quality.file_size_mb} MB`
                            : formatBytes(photo.size)}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2">
          <button
            disabled={page <= 1 || loading}
            onClick={() => fetchPhotos(page - 1)}
            className="px-3 py-2 rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-50 text-sm"
          >
            Prev
          </button>
          <button
            disabled={page >= totalPages || loading}
            onClick={() => fetchPhotos(page + 1)}
            className="px-3 py-2 rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-50 text-sm"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

export default BulkPhotoValidation;

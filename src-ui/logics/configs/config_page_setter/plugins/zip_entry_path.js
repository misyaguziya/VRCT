export const getSafeZipEntryPath = (relativePath) => {
    const normalizedPath = relativePath.replace(/\\/g, "/");
    const pathSegments = normalizedPath.split("/");
    const isAbsolutePath = normalizedPath.startsWith("/") || /^[A-Za-z]:\//.test(normalizedPath);

    if (
        relativePath.includes("\0") ||
        isAbsolutePath ||
        pathSegments.includes("..")
    ) {
        return null;
    }

    const normalizedSegments = pathSegments.filter((part) => part !== "" && part !== ".");
    return normalizedSegments.length > 0 ? normalizedSegments.join("/") : null;
};

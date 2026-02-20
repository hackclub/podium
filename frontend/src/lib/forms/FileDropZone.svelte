<script lang="ts">
	type Props = {
		onfile?: (file: File) => void;
	};

	let { onfile }: Props = $props();

	let dragging = $state(false);
	let selectedFile = $state<File | null>(null);
	let previewUrl = $state<string | null>(null);

	function setFile(file: File) {
		if (previewUrl) URL.revokeObjectURL(previewUrl);
		selectedFile = file;
		previewUrl = URL.createObjectURL(file);
		onfile?.(file);
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		dragging = false;
		const file = e.dataTransfer?.files[0];
		if (file) setFile(file);
	}

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		dragging = true;
	}

	function handleClick() {
		const input = document.createElement('input');
		input.type = 'file';
		input.accept = 'image/*';
		input.onchange = () => {
			const file = input.files?.[0];
			if (file) setFile(file);
		};
		input.click();
	}
</script>

<button
	type="button"
	class="flex w-full cursor-pointer items-center justify-center rounded-xl border-4 border-dashed border-white p-3 text-base text-white drop-shadow-md transition-colors {dragging ? 'bg-white/10' : ''} {previewUrl ? 'h-auto gap-3' : 'h-16'}"
	ondragover={handleDragOver}
	ondragleave={() => (dragging = false)}
	ondrop={handleDrop}
	onclick={handleClick}
>
	{#if previewUrl && selectedFile}
		<img src={previewUrl} alt="preview" class="h-16 w-16 rounded-lg object-cover" />
		<span class="truncate max-w-[12rem] text-sm opacity-90">{selectedFile.name}</span>
	{:else}
		Drag and drop a screenshot
	{/if}
</button>

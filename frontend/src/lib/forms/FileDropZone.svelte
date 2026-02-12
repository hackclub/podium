<script lang="ts">
	type Props = {
		onfile?: (file: File) => void;
	};

	let { onfile }: Props = $props();

	let dragging = $state(false);

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragging = false;
		const file = e.dataTransfer?.files[0];
		if (file) onfile?.(file);
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
			if (file) onfile?.(file);
		};
		input.click();
	}
</script>

<button
	type="button"
	class="flex h-16 w-full cursor-pointer items-center justify-center rounded-xl border-4 border-dashed border-white p-3 text-base text-white drop-shadow-md transition-colors {dragging ? 'bg-white/10' : ''}"
	ondragover={handleDragOver}
	ondragleave={() => (dragging = false)}
	ondrop={handleDrop}
	onclick={handleClick}
>
	Drag and drop a screenshot
</button>

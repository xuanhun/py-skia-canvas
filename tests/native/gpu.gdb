set pagination off
set confirm off
set startup-with-shell off
set print thread-events off
set breakpoint pending on
break canvas_core::gpu::vulkan::engine::VulkanContext::surface
commands
silent
printf "NATIVE_VULKAN_SURFACE_HIT\n"
bt 6
continue
end
break GrVkPrimaryCommandBuffer::submitToQueue
commands
silent
printf "NATIVE_VULKAN_QUEUE_SUBMIT_HIT\n"
bt 5
continue
end
run

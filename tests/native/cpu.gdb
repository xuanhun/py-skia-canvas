set pagination off
set confirm off
set startup-with-shell off
set print thread-events off
set breakpoint pending on
break C_SkSurfaces_Raster
commands
silent
printf "NATIVE_CPU_RASTER_HIT\n"
bt 5
continue
end
break canvas_core::gpu::vulkan::engine::VulkanContext::surface
commands
silent
printf "UNEXPECTED_GPU_SURFACE_HIT\n"
continue
end
break GrVkPrimaryCommandBuffer::submitToQueue
commands
silent
printf "UNEXPECTED_GPU_QUEUE_HIT\n"
continue
end
run
